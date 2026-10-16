"""Export Crimson Desert PAM static meshes to OBJ + MTL.

PAM files are static (non-skinned) world meshes found in game directories
0000 (objects), 0007 (effects), and 0015 (terrain). They share the "PAR "
magic with PAC files but use a different internal structure: flat file with
global bounding box, fixed submesh table at 0x410, and variable vertex stride.

Usage:
    python pam_export.py path/to/mesh.pam -o output_dir/
    python pam_export.py --paz-dir F:/games/CrimsonDesert/0000 --filter "tree" -o output/ --batch
"""

import os
import sys
import struct
import argparse
from dataclasses import dataclass

try:
    import lz4.block
    HAS_LZ4 = True
except ImportError:
    HAS_LZ4 = False

from .pac_export import Vertex, Mesh, write_obj, write_mtl


# ── Data structures ─────────────────────────────────────────────────

@dataclass
class PamSubmesh:
    """Per-submesh entry from the PAM submesh table."""
    nv: int             # vertex count
    ni: int             # index count
    voff: int           # cumulative vertex offset (element count)
    ioff: int           # cumulative index offset (element count)
    texture_name: str   # .dds filename from submesh table
    material_name: str  # material name string


# ── PAM parsing ─────────────────────────────────────────────────────

PAM_VERSIONS = {0x00001802, 0x00001803, 0x01001806}  # known PAM version variants
PAC_VERSION = 0x01000903
SUBMESH_TABLE_OFF = 0x410
SUBMESH_STRIDE = 0x218


def parse_pam_header(data: bytes) -> dict:
    """Parse PAM file header."""
    magic = data[0:4]
    if magic != b'PAR ':
        raise ValueError(f"Not a PAR file (magic: {magic!r})")

    version = struct.unpack_from('<I', data, 4)[0]
    if version == PAC_VERSION:
        raise ValueError("This is a PAC file, not PAM")
    if version not in PAM_VERSIONS:
        raise ValueError(f"Unknown PAM version: 0x{version:08X}")

    mesh_count = struct.unpack_from('<I', data, 0x10)[0]
    bbox_min = struct.unpack_from('<3f', data, 0x14)
    bbox_max = struct.unpack_from('<3f', data, 0x20)
    geom_off = struct.unpack_from('<I', data, 0x3C)[0]
    geom_size = struct.unpack_from('<I', data, 0x40)[0]
    comp_geom_size = struct.unpack_from('<I', data, 0x44)[0]

    return {
        'version': version,
        'mesh_count': mesh_count,
        'bbox_min': bbox_min,
        'bbox_max': bbox_max,
        'geom_off': geom_off,
        'geom_size': geom_size,
        'comp_geom_size': comp_geom_size,
    }


def parse_pam_submeshes(data: bytes, count: int) -> list[PamSubmesh]:
    """Parse submesh table at fixed offset 0x410, stride 0x218."""
    submeshes = []
    for i in range(count):
        off = SUBMESH_TABLE_OFF + i * SUBMESH_STRIDE
        if off + SUBMESH_STRIDE > len(data):
            break
        nv, ni, voff, ioff = struct.unpack_from('<4I', data, off)
        tex_bytes = data[off + 16: off + 16 + 256]
        tex_name = tex_bytes.split(b'\x00', 1)[0].decode('ascii', errors='replace')
        mat_bytes = data[off + 272: off + 272 + 256]
        mat_name = mat_bytes.split(b'\x00', 1)[0].decode('ascii', errors='replace')
        submeshes.append(PamSubmesh(nv=nv, ni=ni, voff=voff, ioff=ioff,
                                    texture_name=tex_name, material_name=mat_name))
    return submeshes


def decompress_pam_geometry(data: bytes) -> bytes:
    """Decompress PAM internal geometry block if LZ4 compressed.

    PAM type 1 files store the header uncompressed and the geometry
    block as a single LZ4 block. Sizes at offsets 0x40 (decomp) and 0x44 (comp).
    """
    comp_size = struct.unpack_from('<I', data, 0x44)[0]
    if comp_size == 0:
        return data

    if not HAS_LZ4:
        raise RuntimeError("lz4 package required: pip install lz4")

    geom_off = struct.unpack_from('<I', data, 0x3C)[0]
    decomp_size = struct.unpack_from('<I', data, 0x40)[0]

    decompressed = lz4.block.decompress(
        data[geom_off:geom_off + comp_size],
        uncompressed_size=decomp_size
    )

    output = bytearray(data[:geom_off])
    output.extend(decompressed)
    footer_start = geom_off + comp_size
    if footer_start < len(data):
        output.extend(data[footer_start:])

    # Mark geometry as uncompressed in header
    struct.pack_into('<I', output, 0x44, 0)
    return bytes(output)


def detect_vertex_stride(header: dict, submeshes: list[PamSubmesh]) -> int:
    """Auto-detect vertex stride: (geom_size - total_ni*2) / total_nv."""
    total_nv = sum(s.nv for s in submeshes)
    total_ni = sum(s.ni for s in submeshes)
    if total_nv == 0:
        return 20

    geom_size = header['geom_size']
    remaining = geom_size - total_ni * 2
    if remaining > 0 and remaining % total_nv == 0:
        return remaining // total_nv

    # Fallback: try common strides
    for s in [20, 24, 28, 32, 36, 40, 16, 12, 8]:
        if total_nv * s + total_ni * 2 <= geom_size:
            return s
    return 20


# ── Vertex / index decoding ────────────────────────────────────────

def decode_pam_vertices(data: bytes, geom_off: int, byte_offset: int,
                        count: int, bbox_min: tuple, bbox_max: tuple,
                        stride: int = 20) -> list[Vertex]:
    """Decode PAM vertices. Position dequant: bbox_min + uint16/65535 * extent."""
    bext = (bbox_max[0] - bbox_min[0],
            bbox_max[1] - bbox_min[1],
            bbox_max[2] - bbox_min[2])
    base = geom_off + byte_offset
    verts = []

    for i in range(count):
        vo = base + i * stride

        px, py, pz = struct.unpack_from('<HHH', data, vo)
        x = bbox_min[0] + (px / 65535.0) * bext[0]
        y = bbox_min[1] + (py / 65535.0) * bext[1]
        z = bbox_min[2] + (pz / 65535.0) * bext[2]

        if stride >= 12:
            u, v = struct.unpack_from('<ee', data, vo + 8)
            u, v = float(u), float(v)
        else:
            u, v = 0.0, 0.0

        if stride >= 16:
            packed = struct.unpack_from('<I', data, vo + 12)[0]
            nx_raw = (packed >> 0) & 0x3FF
            ny_raw = (packed >> 10) & 0x3FF
            nz_raw = (packed >> 20) & 0x3FF
            nx = ny_raw / 511.5 - 1.0
            ny = nz_raw / 511.5 - 1.0
            nz = nx_raw / 511.5 - 1.0
        else:
            nx, ny, nz = 0.0, 1.0, 0.0

        verts.append(Vertex(pos=(x, y, z), uv=(u, v), normal=(nx, ny, nz)))

    return verts


def decode_pam_indices(data: bytes, byte_offset: int, count: int) -> list[int]:
    """Decode u16 triangle indices."""
    return [struct.unpack_from('<H', data, byte_offset + i * 2)[0] for i in range(count)]


# ── Export ──────────────────────────────────────────────────────────

def export_pam(pam_data: bytes, output_dir: str, name_hint: str = "",
               texture_rel_dir: str = "", available_textures: set = None) -> dict:
    """Export a PAM file to OBJ + MTL."""
    header = parse_pam_header(pam_data)
    submeshes = parse_pam_submeshes(pam_data, header['mesh_count'])
    if not submeshes:
        raise ValueError("No submeshes found")

    stride = detect_vertex_stride(header, submeshes)
    total_nv = sum(s.nv for s in submeshes)
    geom_off = header['geom_off']
    idx_byte_start = geom_off + total_nv * stride

    meshes = []
    for sub in submeshes:
        if sub.nv == 0:
            continue

        verts = decode_pam_vertices(
            pam_data, geom_off, sub.voff * stride,
            sub.nv, header['bbox_min'], header['bbox_max'], stride)

        indices = decode_pam_indices(
            pam_data, idx_byte_start + sub.ioff * 2, sub.ni)

        # Material name = texture base (without .dds extension)
        mat_name = sub.texture_name
        if mat_name.lower().endswith('.dds'):
            mat_name = mat_name[:-4]

        meshes.append(Mesh(
            name=sub.material_name or mat_name,
            material=mat_name,
            vertices=verts,
            indices=indices,
        ))

    if not meshes:
        raise ValueError("No meshes with geometry found")

    base_name = name_hint or meshes[0].name.lower().replace(' ', '_')
    obj_filename = base_name + '.obj'
    mtl_filename = base_name + '.mtl'

    os.makedirs(output_dir, exist_ok=True)
    obj_path = os.path.join(output_dir, obj_filename)
    mtl_path = os.path.join(output_dir, mtl_filename)

    write_obj(meshes, obj_path, mtl_filename)
    write_mtl(meshes, mtl_path, texture_rel_dir, available_textures=available_textures)

    return {
        'obj': obj_path, 'mtl': mtl_path,
        'meshes': len(meshes),
        'vertices': sum(len(m.vertices) for m in meshes),
        'triangles': sum(len(m.indices) // 3 for m in meshes),
        'names': [m.name for m in meshes],
    }


# ── CLI ─────────────────────────────────────────────────────────────
