"""Export Crimson Desert PAC skinned meshes to OBJ + MTL.

Parses the PAC binary format (PAR header, 5 sections), extracts mesh geometry
from the highest-detail LOD, and writes Wavefront OBJ + MTL with DDS texture
references.

Usage:
    # Export a single PAC file already on disk
    python pac_export.py path/to/mesh.pac -o output_dir/

    # Export directly from a PAZ archive (requires paz_parse/paz_unpack on sys.path)
    python pac_export.py --paz-dir F:/games/CrimsonDesert/0009 --filter "cd_phw_00_ub_00_0163" -o output/

    # Batch export all uncompressed PHW upper body PACs
    python pac_export.py --paz-dir F:/games/CrimsonDesert/0009 --filter "cd_phw_*_ub_*.pac" -o output/ --batch
"""

import os
import sys
import struct
import argparse
from dataclasses import dataclass, field

try:
    import lz4.block
    HAS_LZ4 = True
except ImportError:
    HAS_LZ4 = False


# ── Data structures ─────────────────────────────────────────────────

@dataclass
class MeshDescriptor:
    """Per-mesh metadata from PAC section 0."""
    display_name: str           # 1st name string (mesh name)
    material_name: str          # 2nd name string (texture base name)
    center: tuple               # (cx, cy, cz) for position dequantization
    half_extent: tuple          # (hx, hy, hz) for position dequantization
    vertex_counts: list         # [lod0, lod1, lod2, lod3] per LOD
    index_counts: list          # [lod0, lod1, lod2, lod3] per LOD
    bbox_unknowns: tuple = ()   # float[0:2], purpose unknown


@dataclass
class Vertex:
    """Decoded vertex data."""
    pos: tuple      # (x, y, z) world-space
    uv: tuple       # (u, v) texture coordinates
    normal: tuple   # (nx, ny, nz) unit normal


@dataclass
class Mesh:
    """Single submesh with geometry and material."""
    name: str
    material: str
    vertices: list = field(default_factory=list)
    indices: list = field(default_factory=list)


# ── PAC parsing ─────────────────────────────────────────────────────

def decompress_type1_pac(raw_data: bytes, orig_size: int) -> bytes:
    """Decompress a type 1 PAC file with internal section-level LZ4.

    Type 1 files store the 80-byte header uncompressed, but individual
    sections may be LZ4 block compressed. The section size table uses
    (u32 comp_size, u32 decomp_size) per slot.
    """
    if not HAS_LZ4:
        raise RuntimeError("lz4 package required for type 1 decompression: pip install lz4")

    output = bytearray(raw_data[:0x50])  # copy 80-byte header
    file_offset = 0x50

    for slot in range(8):
        off = 0x10 + slot * 8
        comp = struct.unpack_from('<I', raw_data, off)[0]
        decomp = struct.unpack_from('<I', raw_data, off + 4)[0]
        if decomp == 0:
            continue
        if comp > 0:
            blob = raw_data[file_offset:file_offset + comp]
            output.extend(lz4.block.decompress(blob, uncompressed_size=decomp))
            file_offset += comp
        else:
            output.extend(raw_data[file_offset:file_offset + decomp])
            file_offset += decomp

    # Fix header: set all comp_size fields to 0 (output is fully decompressed)
    for slot in range(8):
        struct.pack_into('<I', output, 0x10 + slot * 8, 0)

    return bytes(output)


def parse_header(data: bytes) -> dict:
    """Parse 80-byte PAC header. Returns section sizes and offsets."""
    magic = data[0:4]
    if magic != b'PAR ':
        raise ValueError(f"Not a PAC file (magic: {magic!r}, expected b'PAR ')")

    version = struct.unpack_from('<I', data, 4)[0]

    # 8 section slots at offset 0x10, each 8 bytes: [u32_comp_size, u32_decomp_size]
    # If comp_size > 0, section was LZ4 compressed (should be decompressed first)
    # After decompression, comp_size fields are set to 0
    sections = []
    offset = 0x50  # first section starts right after header
    for i in range(8):
        slot_off = 0x10 + i * 8
        comp_size = struct.unpack_from('<I', data, slot_off)[0]
        decomp_size = struct.unpack_from('<I', data, slot_off + 4)[0]
        stored_size = comp_size if comp_size > 0 else decomp_size
        if decomp_size > 0:
            sections.append({'index': i, 'offset': offset, 'size': decomp_size})
            offset += stored_size

    return {'version': version, 'sections': sections}


ATTR4_PATTERN = bytes([0x04, 0x00, 0x01, 0x02, 0x03])  # 4-attribute meshes (standard, 4 LODs)
ATTR3_PATTERN = bytes([0x03, 0x00, 0x01, 0x02])         # 3-attribute meshes (cloth/sim, 3 LODs)
ATTR2_PATTERN = bytes([0x02, 0x00, 0x01])               # 2-attribute meshes (accessories/physics, 2 LODs)


def find_mesh_descriptors(data: bytes, sec0_offset: int, sec0_size: int) -> list[MeshDescriptor]:
    """Find all per-mesh descriptors in section 0 by pattern matching.

    Finds 4-attribute [04 00 01 02 03], 3-attribute [03 00 01 02], and
    2-attribute [02 00 01] meshes. Returns them sorted by position in
    section 0 (matching vertex buffer order in geometry sections).

    Unified layout: vc starts at desc_start+40, ic at desc_start+40+attr_count*2.
    """
    region = data[sec0_offset:sec0_offset + sec0_size]
    found = []  # (offset_in_region, MeshDescriptor)

    # Find 4-attribute descriptors (standard meshes, 4 LODs)
    pos = 0
    while True:
        idx = region.find(ATTR4_PATTERN, pos)
        if idx == -1:
            break
        desc_start = idx - 35
        if desc_start >= 0 and region[desc_start] == 0x01:
            floats = struct.unpack_from('<8f', region, desc_start + 3)
            vc = [struct.unpack_from('<H', region, desc_start + 40 + i * 2)[0] for i in range(4)]
            ic = [struct.unpack_from('<I', region, desc_start + 48 + i * 4)[0] for i in range(4)]
            names = _find_name_strings(region, desc_start)
            found.append((desc_start, MeshDescriptor(
                display_name=names[0], material_name=names[1],
                center=(floats[2], floats[3], floats[4]),
                half_extent=(floats[5], floats[6], floats[7]),
                vertex_counts=vc, index_counts=ic,
                bbox_unknowns=(floats[0], floats[1]),
            )))
        pos = idx + 5

    # Find 3-attribute descriptors (cloth/sim meshes, 3 LODs)
    pos = 0
    while True:
        idx = region.find(ATTR3_PATTERN, pos)
        if idx == -1:
            break
        desc_start = idx - 35
        if desc_start >= 0 and region[desc_start] == 0x01:
            # Skip false positives inside 4-attr patterns
            if idx >= 1 and region[idx - 1] == 0x04:
                pos = idx + 4
                continue
            floats = struct.unpack_from('<8f', region, desc_start + 3)
            vc3 = [struct.unpack_from('<H', region, desc_start + 40 + i * 2)[0] for i in range(3)]
            ic3 = [struct.unpack_from('<I', region, desc_start + 46 + i * 4)[0] for i in range(3)]
            vc = vc3 + [0]  # pad to 4 LODs
            ic = ic3 + [0]
            names = _find_name_strings(region, desc_start)
            found.append((desc_start, MeshDescriptor(
                display_name=names[0], material_name=names[1],
                center=(floats[2], floats[3], floats[4]),
                half_extent=(floats[5], floats[6], floats[7]),
                vertex_counts=vc, index_counts=ic,
                bbox_unknowns=(floats[0], floats[1]),
            )))
        pos = idx + 4

    # Find 2-attribute descriptors (accessories/physics meshes, 2 LODs)
    pos = 0
    while True:
        idx = region.find(ATTR2_PATTERN, pos)
        if idx == -1:
            break
        desc_start = idx - 35
        if desc_start >= 0 and region[desc_start] == 0x01:
            # Skip false positives inside 3-attr or 4-attr patterns
            if idx >= 1 and region[idx - 1] in (0x03, 0x04):
                pos = idx + 3
                continue
            floats = struct.unpack_from('<8f', region, desc_start + 3)
            vc2 = [struct.unpack_from('<H', region, desc_start + 40 + i * 2)[0] for i in range(2)]
            ic2 = [struct.unpack_from('<I', region, desc_start + 44 + i * 4)[0] for i in range(2)]
            # Sanity check: reject if counts look unreasonable (false positive)
            if vc2[0] > 50000 or ic2[0] > 500000:
                pos = idx + 3
                continue
            vc = vc2 + [0, 0]  # pad to 4 LODs
            ic = ic2 + [0, 0]
            names = _find_name_strings(region, desc_start)
            found.append((desc_start, MeshDescriptor(
                display_name=names[0], material_name=names[1],
                center=(floats[2], floats[3], floats[4]),
                half_extent=(floats[5], floats[6], floats[7]),
                vertex_counts=vc, index_counts=ic,
                bbox_unknowns=(floats[0], floats[1]),
            )))
        pos = idx + 3

    # Sort by position in section 0 to match vertex buffer order
    found.sort(key=lambda x: x[0])
    return [desc for _, desc in found]


def _find_name_strings(region: bytes, desc_start: int) -> tuple[str, str]:
    """Extract two length-prefixed name strings before a descriptor.

    Walks backwards from desc_start to find two consecutive
    [u8_len][ASCII_chars] entries.
    """
    # The material name ends right at desc_start.
    # Read its length byte, then the display name before it.
    names = []
    cursor = desc_start

    for _ in range(2):
        # The string occupies [cursor - length ... cursor)
        # and its length byte is at [cursor - length - 1]
        # Search backwards for a plausible length byte
        found = False
        for back in range(1, min(200, cursor+1)):
            candidate_len = region[cursor - back]
            if candidate_len == 0:
                continue
            # Check if this length byte accounts for exactly the right span
            if candidate_len == back - 1:
                name_bytes = region[cursor - back + 1:cursor]
                # Validate: should be printable ASCII
                try:
                    name = name_bytes.decode('ascii')
                    if all(32 <= c < 127 for c in name_bytes):
                        names.append(name)
                        cursor = cursor - back
                        found = True
                        break
                except (UnicodeDecodeError, ValueError):
                    continue
        if not found:
            names.append(f"unknown_{desc_start:x}")

    # We found material_name first (closest to descriptor), then display_name
    names.reverse()
    return (names[0], names[1])


# ── Vertex decoding ─────────────────────────────────────────────────

def decode_vertices(data: bytes, section_offset: int,
                    vertex_count: int, desc: MeshDescriptor,
                    vertex_start: int = 0) -> list[Vertex]:
    """Decode vertices from a geometry section.

    Args:
        data: full PAC file bytes
        section_offset: byte offset of the geometry section
        vertex_count: number of vertices for this mesh
        desc: mesh descriptor with center/half_extent for dequantization
        vertex_start: byte offset within the section where this mesh's verts begin
    """
    STRIDE = 40
    cx, cy, cz = desc.center
    hx, hy, hz = desc.half_extent
    base = section_offset + vertex_start
    verts = []

    for i in range(vertex_count):
        vo = base + i * STRIDE

        # Position: 3 × uint16 at +0, dequantize with per-mesh bbox
        px, py, pz = struct.unpack_from('<HHH', data, vo)
        x = cx + (px / 32767.0) * hx
        y = cy + (py / 32767.0) * hy
        z = cz + (pz / 32767.0) * hz

        # UV: 2 × float16 at +8
        u, v = struct.unpack_from('<ee', data, vo + 8)

        # Normal: R10G10B10A2_UNORM at +16, axes permuted (Y,Z,X)
        packed = struct.unpack_from('<I', data, vo + 16)[0]
        nx_raw = (packed >> 0) & 0x3FF
        ny_raw = (packed >> 10) & 0x3FF
        nz_raw = (packed >> 20) & 0x3FF
        # UNORM → signed float, then permute Y,Z,X
        nx = ny_raw / 511.5 - 1.0
        ny = nz_raw / 511.5 - 1.0
        nz = nx_raw / 511.5 - 1.0

        verts.append(Vertex(pos=(x, y, z), uv=(float(u), float(v)), normal=(nx, ny, nz)))

    return verts


def decode_indices(data: bytes, section_offset: int,
                   index_count: int, total_verts_before: int,
                   index_start: int = 0) -> list[int]:
    """Decode triangle indices from a geometry section.

    Args:
        index_start: byte offset within the section where this mesh's indices begin
                     (after ALL vertex data for ALL meshes)
    """
    base = section_offset + index_start
    indices = []
    for i in range(index_count):
        idx = struct.unpack_from('<H', data, base + i * 2)[0]
        indices.append(idx)
    return indices


# ── Material / texture naming ───────────────────────────────────────

def material_to_dds_basename(mat_name: str) -> str:
    """Convert material name to DDS texture base filename.

    PHW body parts (nude/head) need '_00_' inserted before the numeric ID.
    All other types map directly via lowercase.
    """
    lower = mat_name.lower()

    # PHW body exception: cd_phw_00_nude_XXXX or cd_phw_00_head_XXXX
    if lower.startswith('cd_phw_00_nude_') or lower.startswith('cd_phw_00_head_'):
        prefix_end = len('cd_phw_00_')
        rest = lower[prefix_end:]
        parts = rest.split('_')
        # Insert '00' before the first 4-digit numeric part
        for i, p in enumerate(parts):
            if p.isdigit() and len(p) == 4:
                parts.insert(i, '00')
                break
        return 'cd_phw_00_' + '_'.join(parts)

    return lower


# ── OBJ + MTL writing ──────────────────────────────────────────────

def _find_section_layout(data: bytes, geom_sec: dict, descriptors: list,
                         lod: int, total_indices: int) -> tuple[int, int]:
    """Find vertex start and index start offsets within a geometry section.

    Returns (vert_start, index_start) as byte offsets within the section.

    Standard layout (no gap): [primary verts][primary indices]
    Gap layout: [secondary verts][primary verts][secondary indices][primary indices][extra indices]

    Secondary verts detected by scanning from section start for 40-byte records
    with bytes[36:40] == FF FF FF FF that precede the primary vertex data.
    Primary index start found by scanning for first index value == 0.
    """
    sec_off = geom_sec['offset']
    sec_size = geom_sec['size']
    total_verts = sum(d.vertex_counts[lod] for d in descriptors)

    # No gap — standard layout
    primary_bytes = total_verts * 40
    index_bytes = total_indices * 2
    if primary_bytes + index_bytes >= sec_size:
        return 0, primary_bytes

    gap = sec_size - primary_bytes - index_bytes
    if gap <= 0:
        return 0, primary_bytes

    # Determine layout based on gap size relative to primary data.
    # Large gap (>10% of primary): secondary verts likely BEFORE primary verts
    # Small gap (<10%): secondary verts AFTER primary verts (original layout)
    gap_ratio = gap / max(primary_bytes, 1)

    # Try both layouts and pick the one with better geometry quality:
    # Layout A: [primary verts @ 0][secondary][indices near end]
    # Layout B: [secondary verts @ 0][primary verts][indices after]
    import numpy as _np

    first_vc = next((d.vertex_counts[lod] for d in descriptors if d.vertex_counts[lod] > 0), 0)
    if first_vc == 0:
        return 0, primary_bytes

    secondary_bytes = (gap // 40) * 40

    def _scan_idx_start(after_verts):
        """Find primary index start by scanning for first u16 == 0."""
        for adj in range(0, sec_size - after_verts, 2):
            t = after_verts + adj
            if t + 6 > sec_size:
                break
            if struct.unpack_from('<H', data, sec_off + t)[0] == 0:
                v1 = struct.unpack_from('<H', data, sec_off + t + 2)[0]
                v2 = struct.unpack_from('<H', data, sec_off + t + 4)[0]
                if v1 < first_vc and v2 < first_vc:
                    return t
        return None

    def _measure_quality(v_start, i_start):
        """Measure triangle quality across the mesh (sum of sampled edge lengths)."""
        if i_start is None or i_start + total_indices * 2 > sec_size:
            return 999.0
        verts = decode_vertices(data, sec_off, first_vc,
                                descriptors[0], vertex_start=v_start)
        pos = _np.array([v.pos for v in verts], dtype=_np.float32)
        first_ic = next((d.index_counts[lod] for d in descriptors if d.index_counts[lod] > 0), 0)
        n_tris = first_ic // 3
        # Sample triangles evenly across the entire mesh
        sample_indices = list(range(0, n_tris, max(1, n_tris // 30)))[:30]
        total_edge = 0.0
        for t in sample_indices:
            i0 = struct.unpack_from('<H', data, sec_off + i_start + t * 6)[0]
            i1 = struct.unpack_from('<H', data, sec_off + i_start + t * 6 + 2)[0]
            i2 = struct.unpack_from('<H', data, sec_off + i_start + t * 6 + 4)[0]
            if max(i0, i1, i2) >= len(pos):
                return 999.0
            p0, p1, p2 = pos[i0], pos[i1], pos[i2]
            total_edge += max(float(_np.linalg.norm(p1 - p0)), float(_np.linalg.norm(p2 - p1)),
                              float(_np.linalg.norm(p0 - p2)))
        return total_edge

    # Try every possible secondary vert count (0, 1, 2, ..., gap//40)
    # and pick the one with best first-triangle quality
    best_vs = 0
    best_is = primary_bytes + secondary_bytes
    best_q = _measure_quality(0, best_is) if best_is + total_indices * 2 <= sec_size else 999.0

    if gap // 40 > 4096:raise ValueError('PAC secondary-layout search exceeds supported complexity; choose another LOD')
    for n_sec in range(0, gap // 40 + 1):
        vs = n_sec * 40
        all_end = vs + primary_bytes
        if all_end >= sec_size:
            break
        idx = _scan_idx_start(all_end)
        if idx is None or idx + total_indices * 2 > sec_size:
            continue
        q = _measure_quality(vs, idx)
        if q < best_q:
            best_q = q
            best_vs = vs
            best_is = idx

    return best_vs, best_is

    all_verts_end = vert_start + primary_bytes

    if vert_start == 0:
        # Secondary-after: use gap-adjusted formula (no scan needed)
        secondary_bytes = (gap // 40) * 40
        return 0, primary_bytes + secondary_bytes

    # Secondary-first: scan for primary index start (first u16 == 0 after vertex data)
    first_vc = next((d.vertex_counts[lod] for d in descriptors if d.vertex_counts[lod] > 0), 999)
    for adj in range(0, sec_size - all_verts_end, 2):
        trial = all_verts_end + adj
        if trial + 6 > sec_size:
            break
        v0 = struct.unpack_from('<H', data, sec_off + trial)[0]
        if v0 == 0:
            v1 = struct.unpack_from('<H', data, sec_off + trial + 2)[0]
            v2 = struct.unpack_from('<H', data, sec_off + trial + 4)[0]
            if v1 < first_vc and v2 < first_vc:
                return vert_start, trial

    return vert_start, all_verts_end


def write_mtl(meshes: list[Mesh], mtl_path: str, texture_rel_dir: str = "",
              available_textures: set = None):
    """Write Wavefront MTL file with DDS texture references.

    Args:
        available_textures: if provided, only reference textures in this set (lowercase basenames).
                           If None, reference all textures unconditionally.
    """
    with open(mtl_path, 'w') as f:
        f.write(f"# Materials for {os.path.basename(mtl_path).replace('.mtl', '')}\n\n")

        seen = set()
        for mesh in meshes:
            if mesh.material in seen or mesh.material == "(null)":
                continue
            seen.add(mesh.material)

            dds_base = material_to_dds_basename(mesh.material)
            tex_prefix = (".\\" + texture_rel_dir + "\\" + dds_base) if texture_rel_dir else dds_base

            f.write(f"newmtl {mesh.material}\n")
            f.write("Ka 0.2 0.2 0.2\n")
            f.write("Kd 0.8 0.8 0.8\n")
            f.write("Ks 0.5 0.5 0.5\n")
            f.write("Ns 100.0\n")

            # Only reference textures that exist (if we know what's available)
            def _tex_exists(suffix):
                name = f"{dds_base}{suffix}.dds"
                return available_textures is None or name in available_textures

            # Diffuse: prefer base, fall back to _ma (dye mask) for armor
            if _tex_exists(""):
                f.write(f"map_Kd {tex_prefix}.dds\n")
            elif _tex_exists("_ma"):
                f.write(f"map_Kd {tex_prefix}_ma.dds\n")

            # Normal map
            if _tex_exists("_n"):
                f.write(f"bump {tex_prefix}_n.dds\n")

            # Specular: prefer _sp, fall back to _mg (metallic/gloss)
            if _tex_exists("_sp"):
                f.write(f"map_Ks {tex_prefix}_sp.dds\n")
            elif _tex_exists("_mg"):
                f.write(f"map_Ks {tex_prefix}_mg.dds\n")

            # Displacement (map_disp is standard MTL)
            if _tex_exists("_disp"):
                f.write(f"disp {tex_prefix}_disp.dds\n")

            f.write("\n")


def write_obj(meshes: list[Mesh], obj_path: str, mtl_filename: str):
    """Write Wavefront OBJ file. Y/Z swapped for Blender (Z-up)."""
    with open(obj_path, 'w') as f:
        f.write(f"# Crimson Desert PAC export\n")
        f.write(f"mtllib {mtl_filename}\n\n")

        vert_offset = 0  # OBJ indices are 1-based and global across all meshes

        for mesh in meshes:
            f.write(f"o {mesh.name}\n")
            f.write(f"usemtl {mesh.material}\n")

            # Positions as-is (no axis swap)
            for v in mesh.vertices:
                x, y, z = v.pos
                f.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")

            # Normals as-is
            for v in mesh.vertices:
                nx, ny, nz = v.normal
                f.write(f"vn {nx:.6f} {ny:.6f} {nz:.6f}\n")

            # UVs — flip V
            for v in mesh.vertices:
                u, v_coord = v.uv
                f.write(f"vt {u:.6f} {1.0 - v_coord:.6f}\n")

            # Faces (triangles), 1-based with offset for prior meshes
            for i in range(0, len(mesh.indices), 3):
                i0 = mesh.indices[i] + vert_offset + 1
                i1 = mesh.indices[i + 1] + vert_offset + 1
                i2 = mesh.indices[i + 2] + vert_offset + 1
                f.write(f"f {i0}/{i0}/{i0} {i1}/{i1}/{i1} {i2}/{i2}/{i2}\n")

            vert_offset += len(mesh.vertices)
            f.write("\n")


# ── Main export logic ───────────────────────────────────────────────

def export_pac(pac_data: bytes, output_dir: str, name_hint: str = "",
               texture_rel_dir: str = "", lod: int = 0) -> dict:
    """Export a PAC file to OBJ + MTL.

    Args:
        pac_data: raw PAC file bytes
        output_dir: directory for output files
        name_hint: optional name for output files (default: first mesh name)
        texture_rel_dir: relative path from OBJ to texture directory
        lod: LOD level to export (0=highest detail, 3=lowest)

    Returns:
        dict with export stats
    """
    header = parse_header(pac_data)

    # Map section indices to our sections dict
    sec_by_idx = {s['index']: s for s in header['sections']}
    if 0 not in sec_by_idx:
        raise ValueError("No section 0 (metadata) found")

    sec0 = sec_by_idx[0]

    # LOD 0 → section 4, LOD 1 → section 3, etc.
    geom_section_idx = 4 - lod
    if geom_section_idx not in sec_by_idx:
        raise ValueError(f"No geometry section for LOD {lod} (section {geom_section_idx})")
    geom_sec = sec_by_idx[geom_section_idx]

    # Find mesh descriptors
    descriptors = find_mesh_descriptors(pac_data, sec0['offset'], sec0['size'])
    if not descriptors:
        raise ValueError("No mesh descriptors found in section 0")

    # Build meshes from geometry section
    # Layout: [secondary verts][primary verts][secondary indices][primary indices][extra indices]
    total_verts = sum(d.vertex_counts[lod] for d in descriptors)
    total_indices = sum(d.index_counts[lod] for d in descriptors)
    vert_base, index_byte_offset = _find_section_layout(
        pac_data, geom_sec, descriptors, lod, total_indices)

    # Precompute per-descriptor byte offsets in vertex buffer (after vert_base)
    desc_vert_offsets = []
    off = vert_base
    for d in descriptors:
        desc_vert_offsets.append(off)
        off += d.vertex_counts[lod] * 40

    meshes = []
    # Track partner mesh index for shared buffers (to share Mesh.vertices in OBJ)
    partner_map = {}  # di -> partner_di

    # First pass: detect shared buffers
    idx_off_check = index_byte_offset
    for di, desc in enumerate(descriptors):
        ic = desc.index_counts[lod]
        vc = desc.vertex_counts[lod]
        if vc == 0:
            idx_off_check += ic * 2
            continue
        raw_indices = decode_indices(pac_data, geom_sec['offset'], ic, 0,
                                     index_start=idx_off_check)
        max_idx = max(raw_indices) if raw_indices else 0
        if max_idx >= vc:
            for pj, pd in enumerate(descriptors):
                if pd.vertex_counts[lod] > max_idx and pj != di:
                    partner_map[di] = pj
                    break
        idx_off_check += ic * 2

    # Second pass: build meshes
    for di, desc in enumerate(descriptors):
        vc = desc.vertex_counts[lod]
        ic = desc.index_counts[lod]
        if vc == 0:
            continue

        indices = decode_indices(pac_data, geom_sec['offset'], ic, 0,
                                 index_start=index_byte_offset)

        if di in partner_map:
            pj = partner_map[di]
            vertices = decode_vertices(
                pac_data, geom_sec['offset'], descriptors[pj].vertex_counts[lod], desc,
                vertex_start=desc_vert_offsets[pj]
            )
        else:
            vertices = decode_vertices(
                pac_data, geom_sec['offset'], vc, desc,
                vertex_start=desc_vert_offsets[di]
            )

        meshes.append(Mesh(
            name=desc.display_name,
            material=desc.material_name,
            vertices=vertices,
            indices=indices,
        ))

        index_byte_offset += ic * 2

    if not meshes:
        raise ValueError("No meshes with geometry found")

    # Output filenames
    base_name = name_hint or meshes[0].name.lower()
    base_name = base_name.replace(' ', '_')
    obj_filename = base_name + '.obj'
    mtl_filename = base_name + '.mtl'

    os.makedirs(output_dir, exist_ok=True)
    obj_path = os.path.join(output_dir, obj_filename)
    mtl_path = os.path.join(output_dir, mtl_filename)

    write_obj(meshes, obj_path, mtl_filename)
    write_mtl(meshes, mtl_path, texture_rel_dir)

    total_verts_out = sum(len(m.vertices) for m in meshes)
    total_tris = sum(len(m.indices) // 3 for m in meshes)

    return {
        'obj': obj_path,
        'mtl': mtl_path,
        'meshes': len(meshes),
        'vertices': total_verts_out,
        'triangles': total_tris,
        'names': [m.name for m in meshes],
    }


# ── CLI ─────────────────────────────────────────────────────────────
