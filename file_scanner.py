"""Embedded archive, header, buffer, and compression scanner for AI Generator."""

import bz2
import gzip
import io
import lzma
import math
import os
import re
import struct
import tarfile
import threading
import tkinter as tk
import urllib.parse
import webbrowser
import zipfile
import zlib
from collections import Counter
from dataclasses import dataclass, field
from tkinter import filedialog, messagebox, ttk


HEADERS = {
    'PNG': b'\x89PNG\r\n\x1a\n', 'JPEG': b'\xff\xd8\xff', 'DDS': b'DDS ',
    'BMP': b'BM', 'GIF': b'GIF8', 'RIFF': b'RIFF', 'OGG': b'OggS',
    'WAV/AVI': b'RIFF', 'ZIP': b'PK\x03\x04', 'GZIP': b'\x1f\x8b\x08',
    'BZIP2': b'BZh', 'XZ': b'\xfd7zXZ\x00', '7Z': b"7z\xbc\xaf'\x1c",
    'ZLIB-FAST': b'\x78\x01', 'ZLIB-DEFAULT': b'\x78\x9c',
    'ZLIB-BEST': b'\x78\xda',
    'RAR4': b'Rar!\x1a\x07\x00', 'RAR5': b'Rar!\x1a\x07\x01\x00',
    'PDF': b'%PDF-', 'ELF': b'\x7fELF', 'PE': b'MZ',
    'KTX': b'\xabKTX 11\xbb\r\n\x1a\n',
    'KTX2': b'\xabKTX 20\xbb\r\n\x1a\n', 'PVR': b'PVR\x03',
    'OPENSSL ENCRYPTED': b'Salted__', 'PGP': b'-----BEGIN PGP MESSAGE-----',
}

EXTENSIONS = {
    'PNG': '.png', 'JPEG': '.jpg', 'DDS': '.dds', 'BMP': '.bmp', 'GIF': '.gif',
    'RIFF': '.riff', 'OGG': '.ogg', 'ZIP': '.zip', 'GZIP': '.gz', 'BZIP2': '.bz2',
    'XZ': '.xz', '7Z': '.7z', 'RAR4': '.rar', 'RAR5': '.rar', 'PDF': '.pdf',
    'ELF': '.elf', 'PE': '.exe', 'KTX': '.ktx', 'KTX2': '.ktx2', 'PVR': '.pvr',
    'OPENSSL ENCRYPTED': '.encrypted', 'PGP': '.pgp',
    'ZLIB-FAST': '.bin', 'ZLIB-DEFAULT': '.bin', 'ZLIB-BEST': '.bin',
}


def _size_text(value):
    number = float(max(0, value))
    for unit in ('B', 'KB', 'MB', 'GB'):
        if number < 1024 or unit == 'GB':
            return f'{number:.0f} {unit}' if unit == 'B' else f'{number:.1f} {unit}'
        number /= 1024


def _safe_name(name):
    parts = []
    for part in str(name).replace('\\', '/').split('/'):
        part = part.strip().replace(':', '_')
        if part and part not in ('.', '..'):
            parts.append(part)
    return '/'.join(parts) or 'unnamed'


def _entropy(data):
    if not data:
        return 0.0
    sample = data[:min(len(data), 1024 * 1024)]
    counts = Counter(sample)
    length = len(sample)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


@dataclass
class DataNode:
    name: str
    offset: int
    size: int
    kind: str
    status: str = ''
    data: bytes = b''
    children: list = field(default_factory=list)
    method: str = ''


class FileDataScanner:
    MAX_RESULTS = 5000
    MAX_NESTING = 4

    def __init__(self, parent, on_back=None):
        self.on_back = on_back
        self.window = ttk.Frame(parent, style='App.TFrame')
        self.window.pack(fill=tk.BOTH, expand=True)
        self.path = ''
        self.data = b''
        self.root_node = None
        self.item_nodes = {}
        self.scanning = False
        self.stop_event = threading.Event()
        self._build_ui()

    def _build_ui(self):
        bar = ttk.Frame(self.window, padding=(10, 8, 10, 6))
        bar.pack(fill=tk.X)
        if self.on_back:
            ttk.Button(bar, text='← Back to Home', command=self.request_back).pack(
                side=tk.LEFT, padx=(0, 8))
        self.path_var = tk.StringVar()
        ttk.Entry(bar, textvariable=self.path_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(bar, text='Open Any File', command=self.open_file).pack(side=tk.LEFT, padx=6)
        self.scan_button = ttk.Button(bar, text='Scan Data', command=self.start_scan)
        self.scan_button.pack(side=tk.LEFT)
        self.stop_button = ttk.Button(bar, text='Stop', command=self.stop_scan, state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=(6, 0))


        tools = ttk.Frame(self.window, padding=(10, 0, 10, 6))
        tools.pack(fill=tk.X)
        ttk.Button(tools, text='Expand All', command=lambda: self.set_expanded(True)).pack(side=tk.LEFT)
        ttk.Button(tools, text='Collapse All', command=lambda: self.set_expanded(False)).pack(
            side=tk.LEFT, padx=(6, 0))
        ttk.Button(tools, text='Extract Selected', command=self.extract_selected).pack(
            side=tk.LEFT, padx=(18, 0))
        ttk.Button(tools, text='Extract All / Rebuild Folders', command=self.extract_all).pack(
            side=tk.LEFT, padx=(6, 0))
        self.online_button = ttk.Button(
            tools, text='Search Online', command=self.search_online, state='disabled')
        self.online_button.pack(side=tk.LEFT, padx=(6, 0))
        self.progress = tk.DoubleVar(value=0)
        self.progress_text = tk.StringVar(value='0%')
        self.count_text = tk.StringVar(value='Results: 0')
        ttk.Progressbar(tools, variable=self.progress, maximum=100,
                        style='Accent.Horizontal.TProgressbar').pack(
                            side=tk.LEFT, fill=tk.X, expand=True, padx=(18, 0))
        ttk.Label(tools, textvariable=self.progress_text, width=6).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(tools, textvariable=self.count_text, width=16).pack(side=tk.LEFT)

        cutter = ttk.LabelFrame(self.window, text='Cutter', padding=(8, 5))
        cutter.pack(fill=tk.X, padx=10, pady=(0, 6))
        self.cutter_mode = tk.StringVar(value='Auto')
        self.cutter_offset = tk.StringVar(value='0')
        self.cutter_end = tk.StringVar(value='')
        self.cutter_name = tk.StringVar(value='')
        self.cutter_extension = tk.StringVar(value='.bin')
        self.cutter_info = tk.StringVar(value='Offset 0x00000000 · End 0x00000000 · Size 0 B · Type Unknown')
        ttk.Label(cutter, text='Offset').grid(row=0, column=0, sticky='w')
        ttk.Entry(cutter, textvariable=self.cutter_offset, width=15).grid(row=0, column=1, padx=(4, 6))
        ttk.Combobox(cutter, textvariable=self.cutter_mode,
                     values=('Auto', 'Hex', 'Decimal'), state='readonly', width=9).grid(row=0, column=2)
        ttk.Label(cutter, text='End (blank = EOF)').grid(row=0, column=3, padx=(10, 3))
        ttk.Entry(cutter, textvariable=self.cutter_end, width=15).grid(row=0, column=4)
        ttk.Button(cutter, text='Read Offset', command=self.preview_cut).grid(row=0, column=5, padx=6)
        ttk.Label(cutter, text='Custom name').grid(row=0, column=6, padx=(8, 3))
        ttk.Entry(cutter, textvariable=self.cutter_name, width=16).grid(row=0, column=7)
        ttk.Combobox(cutter, textvariable=self.cutter_extension,
                     values=('.bin', '.dat', '.file', '.ext', '.png', '.jpg', '.dds', '.bmp',
                             '.gif', '.wav', '.ogg', '.zip', '.gz', '.bz2', '.xz', '.7z',
                             '.rar', '.pdf', '.exe', '.elf', '.ktx', '.ktx2', '.pvr'),
                     width=8).grid(row=0, column=8, padx=6)
        ttk.Button(cutter, text='Export Cut', command=self.export_cut).grid(row=0, column=9)
        ttk.Label(cutter, textvariable=self.cutter_info).grid(
            row=1, column=0, columnspan=10, sticky='w', pady=(4, 0))
        cutter.columnconfigure(7, weight=1)

        tree_frame = ttk.Frame(self.window, padding=(10, 0, 10, 6))
        tree_frame.pack(fill=tk.BOTH, expand=True)
        columns = ('offset', 'size', 'type', 'status', 'method')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='tree headings')
        self.tree.heading('#0', text='Hierarchy / Stored Name')
        self.tree.heading('offset', text='Offset')
        self.tree.heading('size', text='Buffer Size')
        self.tree.heading('type', text='Header / Type')
        self.tree.heading('status', text='Status')
        self.tree.heading('method', text='Suggested Method / Tool')
        self.tree.column('#0', width=430, minwidth=180)
        self.tree.column('offset', width=135, anchor='e')
        self.tree.column('size', width=110, anchor='e')
        self.tree.column('type', width=140)
        self.tree.column('status', width=190)
        self.tree.column('method', width=310)
        scroll_y = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        scroll_x = ttk.Scrollbar(tree_frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_selection)
        self.tree.grid(row=0, column=0, sticky='nsew')
        scroll_y.grid(row=0, column=1, sticky='ns')
        scroll_x.grid(row=1, column=0, sticky='ew')
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.status = tk.StringVar(
            value='Open any file to index headers, offsets, buffers, and nested data.')
        ttk.Label(self.window, textvariable=self.status).pack(fill=tk.X, padx=10, pady=(0, 8))

    def open_file(self):
        path = filedialog.askopenfilename(title='Select any file', filetypes=[('All files', '*.*')])
        if not path:
            return
        try:
            with open(path, 'rb') as stream:
                self.data = stream.read()
            self.path = path
            self.path_var.set(path)
            self.status.set(f'Loaded {_size_text(len(self.data))}. Choose Scan Data.')
            self.cutter_offset.set('0');self.cutter_end.set('');self.preview_cut(show_errors=False)
        except Exception as error:
            messagebox.showerror('Open file', str(error))

    def _parse_cutter_offset(self, value):
        text = str(value).strip().replace('_', '')
        if not text:
            return None
        mode = self.cutter_mode.get()
        if mode == 'Hex':
            return int(text[2:] if text.lower().startswith('0x') else text, 16)
        if mode == 'Decimal':
            return int(text, 10)
        return int(text, 16) if text.lower().startswith('0x') else int(text, 10)

    @staticmethod
    def _detect_cut_type(payload):
        for kind, signature in sorted(HEADERS.items(), key=lambda item: len(item[1]), reverse=True):
            if payload.startswith(signature):
                if kind in ('RIFF', 'WAV/AVI') and len(payload) >= 12:
                    form = payload[8:12]
                    if form == b'WAVE': return 'WAV', '.wav'
                    if form == b'AVI ': return 'AVI', '.avi'
                return kind, EXTENSIONS.get(kind, '.bin')
        return 'Unknown', '.bin'

    def _cut_range(self):
        if not self.data:
            raise ValueError('Open an input file first.')
        start = self._parse_cutter_offset(self.cutter_offset.get())
        if start is None:
            raise ValueError('Enter a hexadecimal or decimal starting offset.')
        end_value = self._parse_cutter_offset(self.cutter_end.get())
        end = len(self.data) if end_value is None else end_value
        if start < 0 or start >= len(self.data):
            raise ValueError(f'Start offset must be between 0 and {len(self.data)-1:,}.')
        if end <= start or end > len(self.data):
            raise ValueError(f'End offset must be greater than start and no more than {len(self.data):,}.')
        payload = self.data[start:end]
        kind, detected_ext = self._detect_cut_type(payload)
        return start, end, payload, kind, detected_ext

    def preview_cut(self, show_errors=True):
        try:
            start, end, payload, kind, detected_ext = self._cut_range()
            self.cutter_extension.set(detected_ext)
            self.cutter_info.set(
                f'Offset 0x{start:08X} ({start:,}) · End 0x{end:08X} ({end:,}) · '
                f'Size {_size_text(len(payload))} ({len(payload):,} bytes) · Type {kind}')
            self.status.set(f'Cutter range ready: {kind}, {_size_text(len(payload))}.')
            return start, end, payload, kind, detected_ext
        except Exception as error:
            if show_errors: messagebox.showerror('Cutter', str(error))
            return None

    @staticmethod
    def _unique_export_path(path):
        if not os.path.exists(path): return path
        stem, extension = os.path.splitext(path);number = 1
        while os.path.exists(f'{stem}_{number}{extension}'): number += 1
        return f'{stem}_{number}{extension}'

    def export_cut(self):
        result = self.preview_cut()
        if not result: return
        start, _end, payload, kind, detected_ext = result
        extension = self.cutter_extension.get().strip() or detected_ext
        if not extension.startswith('.'): extension = '.' + extension
        custom = self.cutter_name.get().strip()
        source = os.path.splitext(os.path.basename(self.path))[0] or 'cut'
        base = _safe_name(custom or f'{source}_{start:08X}').replace('/', '_')
        path = filedialog.asksaveasfilename(
            title='Export cut data', initialfile=base + extension,
            defaultextension=extension, filetypes=[(extension.upper().lstrip('.') + ' file', '*' + extension), ('All files', '*.*')])
        if not path: return
        root, chosen = os.path.splitext(path)
        if not chosen: path = path + extension
        path = self._unique_export_path(path)
        try:
            with open(path, 'wb') as stream: stream.write(payload)
            self.status.set(f'Exported {kind} cut: {path}')
        except Exception as error: messagebox.showerror('Cutter export', str(error))


    def start_scan(self):
        if not self.data:
            self.open_file()
        if not self.data or self.scanning:
            return
        self.scanning = True
        self.stop_event.clear()
        self.scan_button.configure(state='disabled')
        self.stop_button.configure(state='normal')
        self._progress(0, 0)
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def stop_scan(self):
        self.stop_event.set()
        self.stop_button.configure(state='disabled')
        self.status.set('Stopping data scan; keeping indexed results…')

    def _scan_worker(self):
        name = os.path.basename(self.path) or 'main_file'
        status = ''
        method = ''
        if self.data.startswith(b'Salted__') or b'-----BEGIN PGP MESSAGE-----' in self.data[:4096]:
            status = 'ENCRYPTED'
            method = self._suggest_decryption(self.data, 'encrypted')
        elif self.data.startswith(b'%PDF-') and b'/Encrypt' in self.data:
            status = 'ENCRYPTED'
            method = 'qpdf or Adobe-compatible PDF tool; valid user/owner password required'
        elif _entropy(self.data) > 7.92:
            status = 'HIGH ENTROPY: compressed or encrypted'
            method = self._suggest_decryption(self.data, 'unknown')
        root = DataNode(name, 0, len(self.data), 'MAIN FILE', status, self.data)
        root.method = method
        self._progress_threadsafe(5, 1)
        try:
            if zipfile.is_zipfile(io.BytesIO(self.data)):
                self._scan_zip(root, self.data, 0)
            elif tarfile.is_tarfile(self.path):
                self._scan_tar(root, self.path)
            else:
                self._scan_compressed_root(root)
                self._scan_headers(root, self.data, 0)
                self._scan_offset_tables(root, self.data)
        except Exception as error:
            root.children.append(DataNode('scan_error.txt', 0, 0, 'ERROR', str(error)))
        count = self._count_nodes(root) - 1
        stopped = self.stop_event.is_set()
        self.window.after(0, lambda: self._finish(root, count, stopped))

    def _suggest_decryption(self, payload, kind='unknown'):
        sample = payload[:min(len(payload), 8 * 1024 * 1024)]
        upper = sample.upper()
        if sample.startswith(b'Salted__'):
            return 'OpenSSL enc; identify cipher/KDF and supply the correct password or key'
        if b'-----BEGIN PGP MESSAGE-----' in sample:
            return 'GnuPG/PGP; matching private key and passphrase required'
        if sample.startswith(b'PK'):
            return '7-Zip/WinRAR/Python ZIP; correct archive password required'
        if sample.startswith(b'7z\xbc\xaf\x27\x1c'):
            return '7-Zip; correct archive password required if headers/data are encrypted'
        if sample.startswith(b'Rar!'):
            return 'WinRAR/7-Zip; correct archive password required'
        hints = []
        algorithms = (
            (b'AES', 'AES'), (b'RIJNDAEL', 'AES/Rijndael'), (b'XTEA', 'XTEA'),
            (b'BLOWFISH', 'Blowfish'), (b'CHACHA', 'ChaCha'), (b'SALSA20', 'Salsa20'),
            (b'DES', 'DES/3DES'), (b'RSA', 'RSA'), (b'XXTEA', 'XXTEA'),
        )
        for marker, label in algorithms:
            if marker in upper and label not in hints:
                hints.append(label)
        if hints:
            return ('Possible ' + ', '.join(hints[:4]) +
                    '; confirm mode, key, IV/nonce, and padding from format documentation or code')
        extension = os.path.splitext(self.path)[1].lower() or 'extensionless format'
        return (f'Unknown/custom {extension}; look for format documentation or a matching '
                'QuickBMS .bms script using the game/archive name. A valid key is still required')

    def _scan_zip(self, parent, payload, depth):
        if depth >= self.MAX_NESTING or self.stop_event.is_set():
            return
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            folders = {}
            for index, info in enumerate(archive.infolist(), 1):
                if self.stop_event.is_set() or self._count_nodes(parent) >= self.MAX_RESULTS:
                    break
                clean = _safe_name(info.filename)
                parts = clean.split('/')
                container = parent
                path_key = ''
                for part in parts[:-1]:
                    path_key = path_key + '/' + part
                    node = folders.get(path_key)
                    if node is None:
                        node = DataNode(part, info.header_offset, 0, 'FOLDER')
                        folders[path_key] = node
                        container.children.append(node)
                    container = node
                encrypted = bool(info.flag_bits & 0x1)
                status = 'ENCRYPTED' if encrypted else (
                    f'DECOMPRESSED from {_size_text(info.compress_size)}'
                    if info.compress_type else 'STORED')
                content = b''
                if not encrypted and not info.is_dir():
                    try:
                        content = archive.read(info)
                    except Exception as error:
                        status = f'ERROR: {error}'
                node = DataNode(parts[-1], info.header_offset, info.file_size,
                                'ZIP ENTRY', status, content)
                if encrypted:
                    node.method = ('7-Zip/WinRAR/ZIP-compatible tool; correct password required. '
                                   'AES ZIP may require a tool with AES support')
                container.children.append(node)
                if content and zipfile.is_zipfile(io.BytesIO(content)):
                    self._scan_zip(node, content, depth + 1)
                self._progress_threadsafe(
                    5 + index / max(1, len(archive.infolist())) * 90,
                    self._count_nodes(parent) - 1)

    def _scan_tar(self, parent, path):
        with tarfile.open(path, 'r:*') as archive:
            members = archive.getmembers()
            folders = {}
            for index, member in enumerate(members, 1):
                if self.stop_event.is_set():
                    break
                clean = _safe_name(member.name)
                parts = clean.split('/')
                container = parent
                path_key = ''
                for part in parts[:-1]:
                    path_key += '/' + part
                    folder = folders.get(path_key)
                    if folder is None:
                        folder = DataNode(part, member.offset, 0, 'FOLDER')
                        folders[path_key] = folder
                        container.children.append(folder)
                    container = folder
                content = b''
                if member.isfile():
                    extracted = archive.extractfile(member)
                    content = extracted.read() if extracted else b''
                container.children.append(DataNode(
                    parts[-1], member.offset_data, member.size,
                    'TAR ENTRY' if member.isfile() else 'FOLDER', '', content))
                self._progress_threadsafe(5 + index / max(1, len(members)) * 90, index)

    def _scan_compressed_root(self, parent):
        decoders = []
        if self.data.startswith(b'\x1f\x8b'):
            decoders.append(('GZIP', gzip.decompress))
        if self.data.startswith(b'BZh'):
            decoders.append(('BZIP2', bz2.decompress))
        if self.data.startswith(b'\xfd7zXZ\x00'):
            decoders.append(('XZ/LZMA', lzma.decompress))
        if len(self.data) > 2 and self.data[0] == 0x78:
            decoders.append(('ZLIB/DEFLATE', zlib.decompress))
        for kind, decoder in decoders:
            try:
                decoded = decoder(self.data)
                node = DataNode(f'decompressed_00000000.bin', 0, len(decoded), kind,
                                'DECOMPRESSED', decoded)
                parent.children.append(node)
                self._scan_headers(node, decoded, 1)
            except Exception:
                continue

    def _scan_headers(self, parent, payload, depth=0):
        hits = []
        total = len(HEADERS)
        for header_number, (kind, signature) in enumerate(HEADERS.items(), 1):
            start = 0
            while not self.stop_event.is_set() and len(hits) < self.MAX_RESULTS:
                offset = payload.find(signature, start)
                if offset < 0:
                    break
                hits.append((offset, kind, signature))
                start = offset + max(1, len(signature))
            self._progress_threadsafe(10 + header_number / total * 85, len(hits))
        hits.sort(key=lambda item: item[0])
        for index, (offset, kind, _signature) in enumerate(hits):
            next_offset = hits[index + 1][0] if index + 1 < len(hits) else len(payload)
            size = max(0, next_offset - offset)
            status = 'ENCRYPTED' if kind in ('OPENSSL ENCRYPTED', 'PGP') else 'INDEXED HEADER'
            extension = EXTENSIONS.get(kind, '.bin')
            name = f'offset_{offset:08X}_{kind.lower().replace("/", "_")}{extension}'
            segment = payload[offset:offset + size]
            node = DataNode(name, offset, size, kind, status, segment)
            if status == 'ENCRYPTED':
                node.method = self._suggest_decryption(segment, kind)
            elif kind in ('7Z', 'RAR4', 'RAR5', 'ZIP'):
                node.method = self._suggest_decryption(segment, kind)
            parent.children.append(node)
            if depth < self.MAX_NESTING and status != 'ENCRYPTED':
                decoded = self._try_decompress(kind, payload[offset:])
                if decoded is not None:
                    decoded_node = DataNode(
                        f'decompressed_{offset:08X}.bin', offset, len(decoded),
                        kind, 'DECOMPRESSED', decoded)
                    node.children.append(decoded_node)
                    self._scan_headers(decoded_node, decoded, depth + 1)

    def _try_decompress(self, kind, payload):
        try:
            if kind == 'GZIP':
                return gzip.decompress(payload)
            if kind == 'BZIP2':
                return bz2.decompress(payload)
            if kind == 'XZ':
                return lzma.decompress(payload)
            if kind.startswith('ZLIB-'):
                decompressor = zlib.decompressobj()
                result = decompressor.decompress(payload)
                result += decompressor.flush()
                return result if result else None
        except (OSError, EOFError, lzma.LZMAError, zlib.error):
            return None
        return None

    def _scan_offset_tables(self, parent, payload):
        """Find plausible LE/BE offset tables and expose their buffer ranges."""
        limit = min(len(payload), 4 * 1024 * 1024)
        names = self._candidate_names(payload)
        tables = []
        occupied_until = {'LE': -1, 'BE': -1}
        for endian_name, endian in (('LE', '<'), ('BE', '>')):
            for base in range(0, max(0, limit - 20), 4):
                if self.stop_event.is_set() or len(tables) >= 40:
                    break
                if base < occupied_until[endian_name]:
                    continue
                values = []
                for index in range(256):
                    position = base + index * 4
                    if position + 4 > limit:
                        break
                    value = struct.unpack_from(endian + 'I', payload, position)[0]
                    if value >= len(payload):
                        break
                    if values and value <= values[-1]:
                        break
                    values.append(value)
                if len(values) < 4:
                    continue
                table_end = base + len(values) * 4
                if values[0] < table_end or values[-1] - values[0] < 64:
                    continue
                tables.append((base, endian_name, values))
                occupied_until[endian_name] = table_end
        for table_number, (base, endian_name, values) in enumerate(tables, 1):
            table_node = DataNode(
                f'offset_table_{table_number:03d}_{endian_name}', base,
                len(values) * 4, f'{endian_name} OFFSET TABLE',
                f'{len(values)} offsets')
            for index, start in enumerate(values):
                end = values[index + 1] if index + 1 < len(values) else len(payload)
                if end <= start:
                    continue
                guessed = names[index] if index < len(names) else f'buffer_{index:04d}.bin'
                table_node.children.append(DataNode(
                    _safe_name(guessed), start, end - start, 'INDEXED BUFFER',
                    'OFFSET-DERIVED', payload[start:end]))
            parent.children.append(table_node)

    def _candidate_names(self, payload):
        names = []
        pattern = re.compile(
            rb'[A-Za-z0-9_./\\-]{3,160}\.(?:png|jpg|jpeg|dds|tga|bmp|wav|ogg|bin|dat|nif|anim|anm|txt)',
            re.IGNORECASE)
        for match in pattern.finditer(payload[:min(len(payload), 8 * 1024 * 1024)]):
            try:
                name = match.group(0).decode('utf-8', 'replace')
                clean = _safe_name(name)
                if clean not in names:
                    names.append(clean)
            except Exception:
                continue
            if len(names) >= 4096:
                break
        return names

    def _count_nodes(self, node):
        return 1 + sum(self._count_nodes(child) for child in node.children)

    def _progress_threadsafe(self, percent, count):
        self.window.after(0, lambda: self._progress(percent, count))

    def _progress(self, percent, count):
        self.progress.set(max(0, min(100, percent)))
        self.progress_text.set(f'{percent:.0f}%')
        self.count_text.set(f'Results: {count:,}')

    def _finish(self, root, count, stopped):
        self.scanning = False
        self.scan_button.configure(state='normal')
        self.stop_button.configure(state='disabled')
        self.root_node = root
        self._progress(100 if not stopped else self.progress.get(), count)
        self._populate_tree()
        self.status.set(
            f'{"Stopped; kept" if stopped else "Scan complete:"} {count:,} indexed items. '
            'Results are from this local scan only. Select an item to optionally search online.')

    def _populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        self.item_nodes.clear()

        def add(node, parent_id=''):
            item_id = self.tree.insert(
                parent_id, 'end', text=node.name, open=(parent_id == ''),
                values=(f'0x{node.offset:08X}', _size_text(node.size),
                        node.kind, node.status, node.method))
            self.item_nodes[item_id] = node
            for child in node.children:
                add(child, item_id)
        if self.root_node:
            add(self.root_node)
        self.online_button.configure(state='disabled')

    def _on_tree_selection(self, _event=None):
        selection = self.tree.selection()
        enabled = bool(selection and self.item_nodes.get(selection[0]))
        self.online_button.configure(state='normal' if enabled else 'disabled')

    def search_online(self):
        """Open a browser search for metadata from the selected local scan result."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning('Search Online', 'Select a scan result first.')
            return
        node = self.item_nodes.get(selection[0])
        if not node:
            return

        source_name = os.path.basename(self.path)
        source_extension = os.path.splitext(source_name)[1]
        selected_extension = os.path.splitext(node.name)[1]
        terms = [source_name, source_extension, node.kind]
        if node.status:
            terms.append(node.status)
        if node.method:
            # Suggested text can contain useful algorithm names, but never file bytes.
            terms.append(node.method)
        if selected_extension and selected_extension != source_extension:
            terms.append(selected_extension)
        query = ' '.join(str(term).strip() for term in terms if str(term).strip())
        query += ' file format compression encryption documentation'
        url = 'https://www.google.com/search?q=' + urllib.parse.quote_plus(query)
        try:
            if not webbrowser.open(url, new=2):
                raise RuntimeError('Windows did not accept the browser request.')
            self.status.set(
                'Opened an online search for the selected result. Local scan results were not changed.')
        except Exception as error:
            messagebox.showerror('Search Online', str(error))

    def set_expanded(self, expanded):
        def walk(item):
            self.tree.item(item, open=expanded)
            for child in self.tree.get_children(item):
                walk(child)
        for root in self.tree.get_children(''):
            walk(root)

    def extract_selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning('Extract data', 'Select an item first.')
            return
        node = self.item_nodes.get(selection[0])
        if not node or not node.data:
            messagebox.showwarning('Extract data', 'This item has no extractable data buffer.')
            return
        path = filedialog.asksaveasfilename(initialfile=os.path.basename(node.name))
        if path:
            try:
                with open(path, 'wb') as stream:
                    stream.write(node.data)
                self.status.set(f'Extracted: {path}')
            except Exception as error:
                messagebox.showerror('Extract data', str(error))

    def extract_all(self):
        if not self.root_node:
            messagebox.showwarning('Extract data', 'Scan a file first.')
            return
        folder = filedialog.askdirectory(title='Select reconstructed output folder')
        if not folder:
            return
        base = os.path.join(folder, _safe_name(os.path.splitext(self.root_node.name)[0]))
        written = 0

        def write_children(node, directory):
            nonlocal written
            os.makedirs(directory, exist_ok=True)
            for child in node.children:
                clean = _safe_name(child.name)
                target = os.path.join(directory, *clean.split('/'))
                if child.children or child.kind == 'FOLDER':
                    write_children(child, target)
                elif child.data:
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with open(target, 'wb') as stream:
                        stream.write(child.data)
                    written += 1
        try:
            write_children(self.root_node, base)
            self.status.set(f'Reconstructed {written:,} files in {base}')
        except Exception as error:
            messagebox.showerror('Extract data', str(error))

    def request_back(self):
        if self.scanning:
            self.stop_event.set()
            self.window.after(75, self.request_back)
            return
        if self.on_back:
            self.on_back(self)


def open_file_scanner(parent, on_back=None):
    return FileDataScanner(parent, on_back=on_back)
