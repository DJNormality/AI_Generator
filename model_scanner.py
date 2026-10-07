"""Generic binary mesh scanner and dependency-free Tk 3D preview."""

import math
import os
import struct
import threading
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk


FORMATS = {
    'Float32': ('f', 4, 1.0),
    'Float16': ('e', 2, 1.0),
    'Int32': ('i', 4, 1.0),
    'UInt32': ('I', 4, 1.0),
    'Int16': ('h', 2, 1.0),
    'UInt16': ('H', 2, 1.0),
    'Int16 normalized': ('h', 2, 1.0 / 32767.0),
    'UInt16 normalized': ('H', 2, 1.0 / 65535.0),
    'Int8': ('b', 1, 1.0),
    'UInt8': ('B', 1, 1.0),
    'Int8 normalized': ('b', 1, 1.0 / 127.0),
    'UInt8 normalized': ('B', 1, 1.0 / 255.0),
}

FLOAT_TYPES = ('Float32', 'Float16', 'Int16 normalized', 'UInt16 normalized',
               'Int16', 'UInt16', 'Int8 normalized', 'UInt8 normalized')
FIXED_TYPES = ('Int16', 'UInt16', 'Int16 normalized', 'UInt16 normalized',
               'Int8', 'UInt8', 'Float32')
CONSOLE_PRESETS = {
    'Generic / Auto': {'endian': 'Auto', 'step': 16, 'types': FLOAT_TYPES},
    'PS1': {'endian': 'Little', 'step': 2, 'types': FIXED_TYPES},
    'PS2': {'endian': 'Little', 'step': 4, 'types': FLOAT_TYPES},
    'PS3': {'endian': 'Big', 'step': 4, 'types': FLOAT_TYPES},
    'PS4': {'endian': 'Little', 'step': 4, 'types': FLOAT_TYPES},
    'PS5': {'endian': 'Little', 'step': 4, 'types': FLOAT_TYPES},
    'Wii': {'endian': 'Big', 'step': 2, 'types': FLOAT_TYPES},
    'GameCube': {'endian': 'Big', 'step': 2, 'types': FLOAT_TYPES},
    'Xbox': {'endian': 'Little', 'step': 4, 'types': FLOAT_TYPES},
    'Xbox 360': {'endian': 'Big', 'step': 4, 'types': FLOAT_TYPES},
    'Xbox One': {'endian': 'Little', 'step': 4, 'types': FLOAT_TYPES},
    'Dreamcast': {'endian': 'Little', 'step': 4, 'types': FLOAT_TYPES},
}

ENDIAN_CODES = {'Little': '<', 'Big': '>'}


def _friendly_size(byte_count):
    value = float(max(0, byte_count))
    units = ('B', 'KB', 'MB', 'GB')
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            return f'{value:.0f} {unit}' if unit == 'B' else f'{value:.1f} {unit}'
        value /= 1024.0


@dataclass
class Candidate:
    score: float
    vertex_offset: int
    vertex_count: int
    stride: int
    position_type: str
    endian: str = 'Little'
    uv_offset: int = 0
    uv_type: str = 'Float32'
    index_offset: int = 0
    index_count: int = 0
    index_type: str = 'UInt16'
    topology: str = 'Triangle list'

    def label(self, item_number=None):
        prefix = f'Item {item_number:03d} | ' if item_number is not None else ''
        assumed_size = max(0, self.vertex_count * self.stride)
        confidence = max(0, min(100, int(self.score + 0.5)))
        byte_order = 'LE' if self.endian == 'Little' else 'BE'
        return (f'{prefix}Offset 0x{self.vertex_offset:08X} | '
                f'Size {_friendly_size(assumed_size)} | {self.vertex_count:,} verts | '
                f'Stride {self.stride} | {self.position_type} {byte_order} | '
                f'{confidence}%')


@dataclass
class BoneCandidate:
    score: float
    offset: int
    bone_count: int
    stride: int
    layout: str
    endian: str = 'Little'
    translation_offsets: tuple = (0, 4, 8)

    def label(self, item_number=None):
        prefix = f'Rig {item_number:03d} | ' if item_number is not None else ''
        confidence = max(0, min(100, int(self.score + 0.5)))
        byte_order = 'LE' if self.endian == 'Little' else 'BE'
        return (f'{prefix}Offset 0x{self.offset:08X} | '
                f'Size {_friendly_size(self.bone_count * self.stride)} | '
                f'{self.bone_count} bones | Stride {self.stride} | '
                f'{self.layout} {byte_order} | {confidence}%')


def _unpack_vector(data, offset, format_name, components, endian='<', value_scale=1.0):
    code, size, scale = FORMATS[format_name]
    end = offset + size * components
    if offset < 0 or end > len(data):
        raise IndexError
    values = struct.unpack_from(endian + code * components, data, offset)
    return tuple(float(value) * scale * value_scale for value in values)


def _position_score(points):
    if len(points) < 8:
        return -1000.0
    if not all(math.isfinite(value) for point in points for value in point):
        return -1000.0
    axes = list(zip(*points))
    spans = [max(axis) - min(axis) for axis in axes]
    if max(spans) <= 1e-8 or sum(span > 1e-6 for span in spans) < 2:
        return -1000.0
    peak = max(abs(value) for point in points for value in point)
    if peak > 1e10:
        return -1000.0
    unique = len({tuple(round(value, 5) for value in point) for point in points})
    jumps = []
    for first, second in zip(points, points[1:]):
        jumps.append(math.sqrt(sum((a - b) ** 2 for a, b in zip(first, second))))
    nonzero = sum(jump > 1e-9 for jump in jumps) / max(1, len(jumps))
    range_bonus = 8 if peak < 1e5 else 2
    return unique / len(points) * 45 + nonzero * 30 + range_bonus + min(15, sum(spans) / max(max(spans), 1e-9) * 5)


class BinaryMeshScanner:
    def __init__(self, parent, embedded=False, on_back=None):
        self.embedded = embedded
        self.on_back = on_back
        if embedded:
            self.window = ttk.Frame(parent, style='App.TFrame')
            self.window.pack(fill=tk.BOTH, expand=True)
        else:
            self.window = tk.Toplevel(parent)
            self.window.title('AI Generator — 3D Model Scanner')
            self.window.geometry('1220x800')
            self.window.minsize(960, 650)
            self.window.configure(bg='#111827')
        self.data = b''
        self.skeleton_data = b''
        self.path = ''
        self.skeleton_path = ''
        self.candidates = []
        self.vertices = []
        self.uvs = []
        self.faces = []
        self.bones = []
        self.yaw = -0.55
        self.pitch = 0.35
        self.zoom = 1.0
        self.drag_origin = None
        self.scanning = False
        self.scan_stop_event = threading.Event()
        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self.window, padding=10)
        top.pack(fill=tk.X)
        if self.embedded:
            ttk.Button(top, text='← Back to Home', command=self.request_back).pack(
                side=tk.LEFT, padx=(0, 10))
        ttk.Label(top, text='Search').pack(side=tk.LEFT, padx=(0, 5))
        self.search_mode = tk.StringVar(value='Geometry')
        self.search_combo = ttk.Combobox(
            top, textvariable=self.search_mode,
            values=['Geometry', 'Animation / Rigging'],
            state='readonly', width=17)
        self.search_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.search_combo.bind('<<ComboboxSelected>>', self.update_search_mode_ui)
        ttk.Label(top, text='Console').pack(side=tk.LEFT, padx=(0, 5))
        self.console_var = tk.StringVar(value='Generic / Auto')
        self.console_combo = ttk.Combobox(
            top, textvariable=self.console_var, values=list(CONSOLE_PRESETS),
            state='readonly', width=14)
        self.console_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.console_combo.bind('<<ComboboxSelected>>', self.apply_console_preset)

        file_row = ttk.Frame(self.window, padding=(10, 0, 10, 6))
        file_row.pack(fill=tk.X)
        self.path_var = tk.StringVar()
        ttk.Entry(file_row, textvariable=self.path_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(file_row, text='Open Any File', command=self.open_file).pack(
            side=tk.LEFT, padx=6)
        ttk.Button(file_row, text='Animation / Skeleton File',
                   command=self.open_skeleton_file).pack(
            side=tk.LEFT, padx=(0, 6))
        self.scan_button = ttk.Button(file_row, text='Scan', command=self.scan)
        self.scan_button.pack(side=tk.LEFT)
        self.deep_scan_button = ttk.Button(
            file_row, text='Deep Rescan', command=self.deep_rescan)
        self.deep_scan_button.pack(side=tk.LEFT, padx=(6, 0))
        self.stop_scan_button = ttk.Button(
            file_row, text='Stop Scan', command=self.stop_scan, state='disabled')
        self.stop_scan_button.pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(file_row, text='Export FBX', command=self.export_fbx).pack(
            side=tk.LEFT, padx=(6, 0))

        scan_info = ttk.Frame(self.window, padding=(10, 0, 10, 8))
        scan_info.pack(fill=tk.X)
        self.scan_progress = tk.DoubleVar(value=0.0)
        self.scan_percent = tk.StringVar(value='0%')
        self.found_items_text = tk.StringVar(value='Results: 0')
        ttk.Progressbar(scan_info, variable=self.scan_progress, maximum=100,
                        mode='determinate',
                        style='Accent.Horizontal.TProgressbar').pack(
                            side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(scan_info, textvariable=self.scan_percent, width=6).pack(
            side=tk.LEFT, padx=(8, 0))
        ttk.Label(scan_info, textvariable=self.found_items_text, width=20).pack(
            side=tk.LEFT, padx=(8, 0))

        body = ttk.Panedwindow(self.window, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        controls = ttk.Frame(body, padding=8)
        viewer = ttk.Frame(body)
        body.add(controls, weight=0)
        body.add(viewer, weight=1)

        candidate_frame = ttk.Frame(controls)
        candidate_frame.grid(row=0, column=0, columnspan=3, sticky='nsew')
        candidate_frame.grid_rowconfigure(0, weight=1)
        candidate_frame.grid_columnconfigure(0, weight=1)
        self.candidate_list = tk.Listbox(
            candidate_frame, width=54, height=8, bg='#0f172a', fg='white',
            exportselection=False)
        self.candidate_list.grid(row=0, column=0, sticky='nsew')
        candidate_scroll = ttk.Scrollbar(
            candidate_frame, orient='vertical', command=self.candidate_list.yview)
        candidate_scroll.grid(row=0, column=1, sticky='ns')
        candidate_scroll_x = ttk.Scrollbar(
            candidate_frame, orient='horizontal', command=self.candidate_list.xview)
        candidate_scroll_x.grid(row=1, column=0, sticky='ew')
        self.candidate_list.configure(yscrollcommand=candidate_scroll.set,
                                      xscrollcommand=candidate_scroll_x.set)
        self.candidate_list.bind('<MouseWheel>', self.scroll_candidates)
        self.candidate_list.bind('<Button-4>', lambda _event: self._scroll_candidate_units(-3))
        self.candidate_list.bind('<Button-5>', lambda _event: self._scroll_candidate_units(3))
        self.candidate_list.bind('<<ListboxSelect>>', self.load_selected_candidate)
        controls.grid_rowconfigure(0, weight=0)

        self.geometry_controls = ttk.Frame(controls)
        self.geometry_controls.grid(row=1, column=0, columnspan=3, sticky='ew')
        self.geometry_controls.grid_columnconfigure(1, weight=1)

        self.vars = {
            'vertex_offset': tk.StringVar(value='0'), 'vertex_count': tk.StringVar(value='0'),
            'stride': tk.StringVar(value='12'), 'position_type': tk.StringVar(value='Float32'),
            'endian': tk.StringVar(value='Little'), 'position_scale': tk.StringVar(value='1.0'),
            'uv_offset': tk.StringVar(value='0'), 'uv_type': tk.StringVar(value='Float32'),
            'index_offset': tk.StringVar(value='0'), 'index_count': tk.StringVar(value='0'),
            'index_type': tk.StringVar(value='UInt16'),
            'topology': tk.StringVar(value='Triangle list'),
        }
        rows = [
            ('Vertex offset', 'vertex_offset'), ('Vertex count', 'vertex_count'),
            ('Vertex stride/padding', 'stride'), ('Position type', 'position_type'),
            ('Byte order', 'endian'), ('Position scale', 'position_scale'),
            ('UV offset in stride', 'uv_offset'), ('UV type', 'uv_type'),
            ('Face/index offset', 'index_offset'), ('Index count', 'index_count'),
            ('Index type', 'index_type'), ('Topology', 'topology'),
        ]
        for row, (label, key) in enumerate(rows, 1):
            compact_row = row - 1
            ttk.Label(self.geometry_controls, text=label).grid(
                row=compact_row, column=0, sticky='w', pady=1)
            if key in ('position_type', 'uv_type', 'index_type', 'topology', 'endian'):
                values = list(FORMATS) if key in ('position_type', 'uv_type') else (
                    ['UInt16', 'UInt32'] if key == 'index_type' else
                    ['Little', 'Big'] if key == 'endian' else
                    ['Triangle list', 'Triangle strip'])
                ttk.Combobox(self.geometry_controls, textvariable=self.vars[key], values=values,
                             state='readonly', width=22).grid(
                                 row=compact_row, column=1, columnspan=2,
                                 sticky='ew', pady=1)
            else:
                ttk.Entry(self.geometry_controls, textvariable=self.vars[key], width=24).grid(
                    row=compact_row, column=1, columnspan=2, sticky='ew', pady=1)
        action_row = len(rows)
        ttk.Button(self.geometry_controls, text='Preview Values',
                   command=self.preview_manual).grid(
            row=action_row, column=0, columnspan=2, sticky='ew', pady=(5, 2))
        ttk.Button(self.geometry_controls, text='Export OBJ', command=self.export_obj).grid(
            row=action_row, column=2, sticky='ew', padx=(5, 0), pady=(5, 2))
        ttk.Button(controls, text='Reset View', command=self.reset_view).grid(
            row=2, column=0, columnspan=3, sticky='ew', pady=(3, 0))
        self.status = tk.StringVar(value='Open any binary file to begin.')
        ttk.Label(controls, textvariable=self.status, wraplength=380).grid(
            row=3, column=0, columnspan=3, sticky='w', pady=(5, 0))

        self.canvas = tk.Canvas(viewer, bg='#020617', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind('<Configure>', lambda _event: self.draw())
        self.canvas.bind('<Control-MouseWheel>', self.on_zoom)
        self.canvas.bind('<Control-Button-4>', lambda _event: self.adjust_zoom(1.12))
        self.canvas.bind('<Control-Button-5>', lambda _event: self.adjust_zoom(0.89))
        self.canvas.bind('<Alt-ButtonPress-1>', self.rotate_start)
        self.canvas.bind('<Alt-B1-Motion>', self.rotate_move)
        self.canvas.create_text(20, 20, anchor='nw', fill='#94a3b8',
                                text='Ctrl + mouse wheel: zoom\nAlt + left drag: rotate')

    @staticmethod
    def _number(value):
        text = str(value).strip().lower()
        return int(text, 16) if text.startswith('0x') else int(text or '0')

    def scroll_candidates(self, event):
        units = -3 if event.delta > 0 else 3
        return self._scroll_candidate_units(units)

    def _scroll_candidate_units(self, units):
        self.candidate_list.yview_scroll(units, 'units')
        return 'break'

    def apply_console_preset(self, _event=None):
        preset = CONSOLE_PRESETS[self.console_var.get()]
        endian = preset['endian']
        if endian != 'Auto':
            self.vars['endian'].set(endian)
        console = self.console_var.get()
        scale = '0.0000305185' if console == 'PS1' else '1.0'
        self.vars['position_scale'].set(scale)
        self.status.set(
            f'{console} preset selected: {endian.lower()}-endian scan, '
            f'{preset["step"]}-byte alignment.')

    def update_search_mode_ui(self, _event=None):
        if self.search_mode.get() == 'Animation / Rigging':
            self.geometry_controls.grid_remove()
            self.status.set(
                'Animation / Rigging mode: load any animation or skeleton file, then scan.')
        else:
            self.geometry_controls.grid()
            self.status.set('Geometry mode: open any model file, then scan.')

    def open_file(self):
        path = filedialog.askopenfilename(title='Select any possible 3D model file',
                                          filetypes=[('All files', '*.*')])
        if not path:
            return
        try:
            size = os.path.getsize(path)
            if size > 1024 ** 3 and not messagebox.askyesno(
                    'Large file', f'This file is {size / 1024**3:.1f} GB. Load it anyway?'):
                return
            with open(path, 'rb') as stream:
                self.data = stream.read()
            self.path = path
            self.path_var.set(path)
            format_note = self._detect_console_container()
            self.status.set(f'Loaded {len(self.data):,} bytes. {format_note} Choose Scan.')
        except Exception as error:
            messagebox.showerror('Open model file', str(error))

    def open_skeleton_file(self):
        path = filedialog.askopenfilename(
            title='Select an optional skeleton, rig, animation, or DAT file',
            filetypes=[('All files', '*.*')])
        if not path:
            return
        try:
            with open(path, 'rb') as stream:
                self.skeleton_data = stream.read()
            self.skeleton_path = path
            self.path_var.set(path)
            self.search_mode.set('Animation / Rigging')
            self.update_search_mode_ui()
            self.status.set(
                f'Skeleton file loaded: {os.path.basename(path)} '
                f'({_friendly_size(len(self.skeleton_data))}). Choose Scan.')
        except Exception as error:
            messagebox.showerror('Open skeleton file', str(error))

    def _detect_console_container(self):
        header = self.data[:4096]
        if header.startswith(b'Gamebryo File Format'):
            if b'SRWiiDisplayList' in header:
                self.console_var.set('Wii')
                self.apply_console_preset()
                return ('Wii Gamebryo NIF with SRWiiDisplayList detected; its render stream '
                        'uses console-specific packing. ')
            if b'NiPS2GeometryStreamer' in header:
                self.console_var.set('PS2')
                self.apply_console_preset()
                return ('PS2 Gamebryo NIF with NiPS2GeometryStreamer detected; its render '
                        'stream uses console-specific packing. ')
            return 'Gamebryo NIF detected. '
        return ''

    def scan(self):
        if self.search_mode.get() == 'Animation / Rigging' and self.skeleton_data:
            pass
        elif not self.data:
            self.open_file()
        if self.search_mode.get() == 'Animation / Rigging':
            if not (self.skeleton_data or self.data):
                return
        elif not self.data:
            return
        if self.scanning:
            return
        self.scanning = True
        self.scan_stop_event.clear()
        self.scan_button.configure(state='disabled')
        self.deep_scan_button.configure(state='disabled')
        self.stop_scan_button.configure(state='normal')
        self._report_scan_progress(0, 0)
        if self.search_mode.get() == 'Animation / Rigging':
            self.status.set('Searching for bone matrices, TRS transforms, and hierarchy data…')
        else:
            self.status.set('Scanning common offsets, strides, padding, and numeric types…')
        threading.Thread(target=self._scan_worker, args=(False,), daemon=True).start()

    def deep_rescan(self):
        if self.search_mode.get() == 'Animation / Rigging' and self.skeleton_data:
            pass
        elif not self.data:
            self.open_file()
        active_data = self.skeleton_data if (
            self.search_mode.get() == 'Animation / Rigging' and self.skeleton_data) else self.data
        if not active_data or self.scanning:
            return
        self.scanning = True
        self.scan_stop_event.clear()
        self.scan_button.configure(state='disabled')
        self.deep_scan_button.configure(state='disabled')
        self.stop_scan_button.configure(state='normal')
        self._report_scan_progress(0, 0)
        self.status.set('Deep rescanning near the current offset with finer alignment…')
        threading.Thread(target=self._scan_worker, args=(True,), daemon=True).start()

    def stop_scan(self):
        if not self.scanning:
            return
        self.scan_stop_event.set()
        self.stop_scan_button.configure(state='disabled')
        self.status.set('Stopping scan… keeping candidates already found.')

    def _scan_worker(self, deep=False):
        try:
            if self.search_mode.get() == 'Animation / Rigging':
                self._scan_bone_candidates(deep)
            else:
                self._scan_candidates(deep)
        except Exception as error:
            self.window.after(0, lambda err=error: self._scan_failed(err))

    def _scan_failed(self, error):
        self.scanning = False
        self.scan_button.configure(state='normal')
        self.deep_scan_button.configure(state='normal')
        self.stop_scan_button.configure(state='disabled')
        self.status.set('Scan failed. Adjust the file or try manual values.')
        messagebox.showerror('3D model scan', str(error))

    def _report_scan_progress(self, percent, found):
        self.scan_progress.set(max(0.0, min(100.0, float(percent))))
        self.scan_percent.set(f'{percent:.0f}%')
        self.found_items_text.set(f'Results: {found:,}')

    def request_back(self):
        if self.scanning:
            self.scan_stop_event.set()
            self.stop_scan_button.configure(state='disabled')
            self.status.set('Stopping scan before returning home…')
            self.window.after(75, self.request_back)
            return
        if self.on_back:
            self.on_back(self)
        elif not self.embedded:
            self.window.destroy()

    def _scan_candidates(self, deep=False):
        candidates = []
        strides = tuple(range(6, 161, 2)) if deep else (
            6, 8, 10, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48,
            56, 64, 72, 80, 96, 112, 128, 144, 160)
        limit = len(self.data)
        preset = CONSOLE_PRESETS[self.console_var.get()]
        position_types = preset['types']
        endian_names = ('Little', 'Big') if preset['endian'] == 'Auto' else (preset['endian'],)
        if deep:
            try:
                center = self._number(self.vars['vertex_offset'].get())
            except ValueError:
                center = 0
            radius = min(131072, max(8192, limit // 32))
            start, stop = max(0, center - radius), min(limit, center + radius)
            anchors = range(start, stop, max(1, preset['step']))
        else:
            # Probe densely near likely headers and evenly across the remainder,
            # but keep work bounded for very large containers.
            anchors = set(range(0, min(limit, 1024 * 1024), 256))
            anchors.update(range(0, limit, max(4096, limit // 2048 or 1)))
        sorted_anchors = sorted(anchors)
        anchor_total = max(1, len(sorted_anchors))
        for anchor_index, offset in enumerate(sorted_anchors, 1):
            if self.scan_stop_event.is_set():
                break
            for endian_name in endian_names:
                if self.scan_stop_event.is_set():
                    break
                endian_code = ENDIAN_CODES[endian_name]
                for type_name in position_types:
                    if self.scan_stop_event.is_set():
                        break
                    component_size = FORMATS[type_name][1]
                    for stride in strides:
                        if self.scan_stop_event.is_set():
                            break
                        if stride < component_size * 3 or offset + stride * 16 > limit:
                            continue
                        points = []
                        try:
                            sample_count = 16 if deep else 24
                            for index in range(sample_count):
                                points.append(_unpack_vector(
                                    self.data, offset + index * stride, type_name, 3,
                                    endian_code))
                        except (IndexError, struct.error):
                            continue
                        score = _position_score(points)
                        if score < 60:
                            continue
                        maximum_count = min(100000, (limit - offset) // stride)
                        count = maximum_count
                        candidates.append(Candidate(
                            score=score, vertex_offset=offset,
                            vertex_count=count, stride=stride,
                            position_type=type_name, endian=endian_name,
                            uv_offset=component_size * 3, uv_type='Float32',
                            index_offset=0, index_count=0,
                            index_type='UInt16', topology='Triangle list'))
            if anchor_index == 1 or anchor_index % 32 == 0 or anchor_index == anchor_total:
                percent = anchor_index / anchor_total * 88.0
                found = len(candidates)
                self.window.after(
                    0, lambda p=percent, f=found: self._report_scan_progress(p, f))
        candidates.sort(key=lambda item: item.score, reverse=True)
        # Index probing is much more expensive than position scoring, so apply
        # it only to the best position layouts.
        index_candidates = candidates[:300]
        for index_number, candidate in enumerate(index_candidates, 1):
            if self.scan_stop_event.is_set():
                break
            endian_code = ENDIAN_CODES[candidate.endian]
            maximum_count = min(100000, (limit - candidate.vertex_offset) // candidate.stride)
            possible_counts = [maximum_count]
            best_index = (0, 0, 'UInt16', 0, possible_counts[0])
            for possible_count in possible_counts:
                found = self._find_indices(
                    candidate.vertex_offset, possible_count,
                    candidate.stride, endian_code)
                if found[3] > best_index[3]:
                    best_index = (*found, possible_count)
            (candidate.index_offset, candidate.index_count,
             candidate.index_type, index_score, candidate.vertex_count) = best_index
            candidate.score += index_score
            if index_number == 1 or index_number % 20 == 0 or index_number == len(index_candidates):
                percent = 88.0 + index_number / max(1, len(index_candidates)) * 10.0
                found = len(candidates)
                self.window.after(
                    0, lambda p=percent, f=found: self._report_scan_progress(p, f))
        candidates.sort(key=lambda item: item.score, reverse=True)
        unique = []
        seen = set()
        for candidate in candidates:
            key = (candidate.vertex_offset, candidate.stride,
                   candidate.position_type, candidate.endian)
            if key not in seen:
                seen.add(key)
                unique.append(candidate)
            if len(unique) >= 100:
                break
        stopped = self.scan_stop_event.is_set()
        self.window.after(0, lambda: self._finish_scan(unique, stopped))

    def _scan_bone_candidates(self, deep=False):
        data = self.skeleton_data or self.data
        preset = CONSOLE_PRESETS[self.console_var.get()]
        endian_names = ('Little', 'Big') if preset['endian'] == 'Auto' else (preset['endian'],)
        layouts = [
            ('Matrix 4x4 F32 row', 'Float32', (12, 28, 44), (64, 80, 96, 128)),
            ('Matrix 4x4 F32 column', 'Float32', (48, 52, 56), (64, 80, 96, 128)),
            ('Matrix 3x4 F32', 'Float32', (12, 28, 44), (48, 64, 80, 96)),
            ('TRS F32', 'Float32', (0, 4, 8), (40, 48, 64, 80)),
            ('Matrix 4x4 F16 row', 'Float16', (6, 14, 22), (32, 40, 48, 64)),
            ('Matrix 4x4 F16 column', 'Float16', (24, 26, 28), (32, 40, 48, 64)),
        ]
        if deep and getattr(self, 'current_bone_candidate', None):
            center = self.current_bone_candidate.offset
            start, stop, step = max(0, center - 32768), min(len(data), center + 32768), 2
        elif deep:
            start, stop, step = 0, min(len(data), 262144), 2
        else:
            start, stop = 0, len(data)
            step = max(16, len(data) // 8192 or 1)
        anchors = list(range(start, stop, step))
        candidates = []
        total = max(1, len(anchors))
        for anchor_number, offset in enumerate(anchors, 1):
            if self.scan_stop_event.is_set():
                break
            for endian_name in endian_names:
                endian = ENDIAN_CODES[endian_name]
                for layout_name, value_type, translation_offsets, strides in layouts:
                    for stride in strides:
                        if self.scan_stop_event.is_set():
                            break
                        positions = []
                        try:
                            for bone_index in range(10):
                                base = offset + bone_index * stride
                                position = tuple(
                                    _unpack_vector(data, base + component_offset,
                                                   value_type, 1, endian)[0]
                                    for component_offset in translation_offsets)
                                positions.append(position)
                        except (IndexError, struct.error, OverflowError):
                            continue
                        score = _position_score(positions)
                        if score < 55:
                            continue
                        bone_count = self._estimate_bone_count(
                            data, offset, stride, value_type,
                            translation_offsets, endian)
                        if bone_count < 2:
                            continue
                        candidates.append(BoneCandidate(
                            score=min(100, score + min(10, bone_count / 8)),
                            offset=offset, bone_count=bone_count, stride=stride,
                            layout=layout_name, endian=endian_name,
                            translation_offsets=translation_offsets))
            if anchor_number == 1 or anchor_number % 32 == 0 or anchor_number == total:
                percent = anchor_number / total * 98
                found = len(candidates)
                self.window.after(
                    0, lambda p=percent, f=found: self._report_scan_progress(p, f))
        candidates.sort(key=lambda item: item.score, reverse=True)
        unique, seen = [], set()
        for candidate in candidates:
            key = (candidate.offset, candidate.stride,
                   candidate.layout, candidate.endian)
            if key in seen:
                continue
            seen.add(key)
            unique.append(candidate)
            if len(unique) >= 100:
                break
        stopped = self.scan_stop_event.is_set()
        self.window.after(0, lambda: self._finish_scan(unique, stopped))

    def _estimate_bone_count(self, data, offset, stride, value_type,
                             translation_offsets, endian):
        count = 0
        for bone_index in range(512):
            base = offset + bone_index * stride
            try:
                position = tuple(
                    _unpack_vector(data, base + component_offset,
                                   value_type, 1, endian)[0]
                    for component_offset in translation_offsets)
            except (IndexError, struct.error, OverflowError):
                break
            if not all(math.isfinite(value) and abs(value) < 1e8 for value in position):
                break
            count += 1
        return count

    def _finish_scan(self, unique, stopped=False):
        self.scanning = False
        self.scan_button.configure(state='normal')
        self.deep_scan_button.configure(state='normal')
        self.stop_scan_button.configure(state='disabled')
        self.candidates = unique
        if not stopped:
            self._report_scan_progress(100, len(unique))
        else:
            self.found_items_text.set(f'Results: {len(unique):,}')
        self.candidate_list.delete(0, tk.END)
        for item_number, candidate in enumerate(unique, 1):
            self.candidate_list.insert(tk.END, candidate.label(item_number))
        if stopped:
            self.status.set(
                f'Scan stopped. Kept {len(unique)} ranked items found so far.')
        else:
            self.status.set(
                f'Found {len(unique)} ranked items. Select one or enter values manually.')
        if unique:
            self.candidate_list.selection_set(0)
            if not stopped:
                if isinstance(unique[0], BoneCandidate):
                    self.load_bone_candidate(unique[0])
                else:
                    self.load_candidate(unique[0])

    def _find_indices(self, vertex_offset, vertex_count, stride, endian='<'):
        start = min(len(self.data), vertex_offset + vertex_count * stride)
        for padding in range(0, 260, 4):
            if self.scan_stop_event.is_set():
                return 0, 0, 'UInt16', 0
            offset = start + padding
            for name, code, size in (('UInt16', 'H', 2), ('UInt32', 'I', 4)):
                if offset + size * 12 > len(self.data):
                    continue
                values = []
                for index in range(min(3000, (len(self.data) - offset) // size)):
                    if index % 128 == 0 and self.scan_stop_event.is_set():
                        return 0, 0, 'UInt16', 0
                    value = struct.unpack_from(endian + code, self.data, offset + index * size)[0]
                    if value >= vertex_count:
                        break
                    values.append(value)
                valid_triangles = sum(1 for i in range(0, len(values) - 2, 3)
                                      if len({values[i], values[i+1], values[i+2]}) == 3)
                if valid_triangles >= 4:
                    return offset, len(values) // 3 * 3, name, min(25, valid_triangles / 2)
        return 0, 0, 'UInt16', 0

    def load_selected_candidate(self, _event=None):
        selected = self.candidate_list.curselection()
        if selected:
            candidate = self.candidates[selected[0]]
            if isinstance(candidate, BoneCandidate):
                self.load_bone_candidate(candidate)
            else:
                self.load_candidate(candidate)

    def load_bone_candidate(self, candidate):
        data = self.skeleton_data or self.data
        endian = ENDIAN_CODES[candidate.endian]
        value_type = 'Float16' if 'F16' in candidate.layout else 'Float32'
        bones = []
        for bone_index in range(candidate.bone_count):
            base = candidate.offset + bone_index * candidate.stride
            try:
                position = tuple(
                    _unpack_vector(data, base + component_offset,
                                   value_type, 1, endian)[0]
                    for component_offset in candidate.translation_offsets)
            except (IndexError, struct.error, OverflowError):
                break
            parent = bone_index - 1 if bone_index else -1
            bones.append((parent, position))
        self.current_bone_candidate = candidate
        self.bones = bones
        self.status.set(
            f'Merged rig preview: {len(bones):,} assumed bones from '
            f'{os.path.basename(self.skeleton_path or self.path)}. '
            'Bright red lines show bones; X/Y/Z labels show local axes.')
        self.reset_view()

    def load_candidate(self, candidate):
        values = {
            'vertex_offset': candidate.vertex_offset, 'vertex_count': candidate.vertex_count,
            'stride': candidate.stride, 'position_type': candidate.position_type,
            'endian': candidate.endian,
            'uv_offset': candidate.uv_offset, 'uv_type': candidate.uv_type,
            'index_offset': candidate.index_offset, 'index_count': candidate.index_count,
            'index_type': candidate.index_type, 'topology': candidate.topology,
        }
        for key, value in values.items():
            self.vars[key].set(str(value))
        self.preview_manual()

    def preview_manual(self):
        try:
            offset = self._number(self.vars['vertex_offset'].get())
            count = min(250000, self._number(self.vars['vertex_count'].get()))
            stride = self._number(self.vars['stride'].get())
            position_type = self.vars['position_type'].get()
            endian = ENDIAN_CODES[self.vars['endian'].get()]
            value_scale = float(self.vars['position_scale'].get() or '1')
            uv_offset = self._number(self.vars['uv_offset'].get())
            uv_type = self.vars['uv_type'].get()
            self.vertices = [_unpack_vector(
                self.data, offset + i * stride, position_type, 3, endian, value_scale)
                             for i in range(count)]
            self.uvs = []
            try:
                self.uvs = [_unpack_vector(
                    self.data, offset + i * stride + uv_offset, uv_type, 2, endian)
                            for i in range(count)]
            except Exception:
                self.uvs = []
            self.faces = self._read_faces(count)
            self.status.set(f'Previewing {len(self.vertices):,} vertices and {len(self.faces):,} faces.')
            self.reset_view()
        except Exception as error:
            self.vertices = []
            self.faces = []
            self.draw()
            messagebox.showerror('Preview model candidate', str(error))

    def _read_faces(self, vertex_count):
        offset = self._number(self.vars['index_offset'].get())
        count = self._number(self.vars['index_count'].get())
        if count <= 0:
            return [(i, i + 1, i + 2) for i in range(0, min(vertex_count - 2, 30000), 3)]
        name = self.vars['index_type'].get()
        code, size = ('H', 2) if name == 'UInt16' else ('I', 4)
        endian = ENDIAN_CODES[self.vars['endian'].get()]
        values = [struct.unpack_from(endian + code, self.data, offset + i * size)[0]
                  for i in range(count)]
        topology = self.vars['topology'].get()
        if topology == 'Triangle strip':
            return [(values[i], values[i + 1], values[i + 2]) if i % 2 == 0
                    else (values[i + 1], values[i], values[i + 2])
                    for i in range(len(values) - 2)
                    if max(values[i:i+3]) < vertex_count and len(set(values[i:i+3])) == 3]
        return [tuple(values[i:i+3]) for i in range(0, len(values) - 2, 3)
                if max(values[i:i+3]) < vertex_count and len(set(values[i:i+3])) == 3]

    def reset_view(self):
        self.yaw, self.pitch, self.zoom = -0.55, 0.35, 1.0
        self.draw()

    def on_zoom(self, event):
        self.adjust_zoom(1.12 if event.delta > 0 else 0.89)

    def adjust_zoom(self, factor):
        self.zoom = max(0.05, min(100.0, self.zoom * factor))
        self.draw()

    def rotate_start(self, event):
        self.drag_origin = (event.x, event.y, self.yaw, self.pitch)

    def rotate_move(self, event):
        if not self.drag_origin:
            return
        x, y, yaw, pitch = self.drag_origin
        self.yaw = yaw + (event.x - x) * 0.01
        self.pitch = max(-math.pi / 2, min(math.pi / 2, pitch + (event.y - y) * 0.01))
        self.draw()

    def draw(self):
        self.canvas.delete('mesh')
        bone_points = [position for _parent, position in self.bones]
        all_points = list(self.vertices) + bone_points
        if not all_points:
            return
        width, height = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        sample = all_points[:min(len(all_points), 100000)]
        center = tuple((min(axis) + max(axis)) / 2 for axis in zip(*sample))
        radius = max(math.sqrt(sum((value - center[i]) ** 2 for i, value in enumerate(point)))
                     for point in sample) or 1.0
        cy, sy = math.cos(self.yaw), math.sin(self.yaw)
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        scale = min(width, height) * 0.42 * self.zoom / radius
        def project(point):
            x, y, z = point
            x, y, z = x-center[0], y-center[1], z-center[2]
            rx, rz = x*cy + z*sy, -x*sy + z*cy
            ry, rz = y*cp - rz*sp, y*sp + rz*cp
            return width/2 + rx*scale, height/2 - ry*scale, rz

        projected = [project(vertex) for vertex in self.vertices]
        faces = self.faces[:20000]
        faces = sorted(faces, key=lambda face: sum(projected[i][2] for i in face) / 3)
        for face in faces:
            try:
                points = [(projected[i][0], projected[i][1]) for i in face]
                flat = [value for point in points for value in point]
                self.canvas.create_polygon(*flat, fill='#1e3a5f', outline='#60a5fa',
                                           width=1, tags='mesh')
            except (IndexError, tk.TclError):
                continue
        if not faces:
            for x, y, _z in projected[:30000]:
                self.canvas.create_oval(x-1, y-1, x+1, y+1, fill='#60a5fa',
                                        outline='', tags='mesh')
        if self.bones:
            projected_bones = [project(position) for _parent, position in self.bones]
            for bone_index, (parent, _position) in enumerate(self.bones):
                x, y, _z = projected_bones[bone_index]
                if 0 <= parent < len(projected_bones):
                    px, py, _pz = projected_bones[parent]
                    self.canvas.create_line(
                        px, py, x, y, fill='#ff2020', width=3, tags='mesh')
                self.canvas.create_oval(
                    x-4, y-4, x+4, y+4, fill='#ff3030', outline='#ffffff',
                    width=1, tags='mesh')
                if bone_index < 128:
                    axis_length = radius * 0.045
                    origin = self.bones[bone_index][1]
                    axes = (
                        ('X', (axis_length, 0, 0), '#ff4040'),
                        ('Y', (0, axis_length, 0), '#40ff70'),
                        ('Z', (0, 0, axis_length), '#4090ff'),
                    )
                    for label, delta, color in axes:
                        endpoint = tuple(origin[i] + delta[i] for i in range(3))
                        ex, ey, _ez = project(endpoint)
                        self.canvas.create_line(
                            x, y, ex, ey, fill=color, width=2, tags='mesh')
                        self.canvas.create_text(
                            ex+4, ey, text=label, fill=color,
                            font=('Segoe UI Semibold', 8), anchor='w', tags='mesh')
                    self.canvas.create_text(
                        x+6, y-7, text=str(bone_index), fill='#ff8080',
                        font=('Segoe UI', 8), anchor='w', tags='mesh')

    def export_obj(self):
        if not self.vertices:
            messagebox.showwarning('Export OBJ', 'Preview a valid candidate first.')
            return
        path = filedialog.asksaveasfilename(defaultextension='.obj',
                                            filetypes=[('Wavefront OBJ', '*.obj')])
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8', newline='\n') as stream:
                stream.write('# Exported by AI Generator 3D Model Scanner\n')
                for x, y, z in self.vertices:
                    stream.write(f'v {x:.9g} {y:.9g} {z:.9g}\n')
                if len(self.uvs) == len(self.vertices):
                    for u, v in self.uvs:
                        stream.write(f'vt {u:.9g} {v:.9g}\n')
                for a, b, c in self.faces:
                    if len(self.uvs) == len(self.vertices):
                        stream.write(f'f {a+1}/{a+1} {b+1}/{b+1} {c+1}/{c+1}\n')
                    else:
                        stream.write(f'f {a+1} {b+1} {c+1}\n')
            self.status.set(f'Exported OBJ: {path}')
        except Exception as error:
            messagebox.showerror('Export OBJ', str(error))

    def export_fbx(self):
        path = filedialog.asksaveasfilename(
            title='Export scanned model as FBX', defaultextension='.fbx',
            filetypes=[('Autodesk FBX', '*.fbx'), ('All files', '*.*')])
        if not path:
            return
        try:
            vertices = [tuple(map(float, vertex[:3])) for vertex in self.vertices]
            faces = [tuple(map(int, face[:3])) for face in self.faces
                     if len(face) >= 3 and min(face[:3]) >= 0 and
                     max(face[:3]) < len(vertices)]
            vertex_values = ','.join(
                f'{value:.9g}' for vertex in vertices for value in vertex)
            polygon_values = ','.join(
                str(value) for a, b, c in faces for value in (a, b, -(c + 1)))
            vertex_count = len(vertices) * 3
            polygon_count = len(faces) * 3
            bone_objects = []
            bone_connections = []
            for bone_index, (parent, position) in enumerate(self.bones):
                bone_id = 200000 + bone_index
                if 0 <= parent < len(self.bones):
                    parent_position = self.bones[parent][1]
                    local_position = tuple(
                        position[i] - parent_position[i] for i in range(3))
                    parent_id = 200000 + parent
                else:
                    local_position = position
                    parent_id = 100001
                bone_objects.append(f'''    Model: {bone_id}, "Model::Bone_{bone_index:03d}", "LimbNode" {{
        Version: 232
        Properties70:  {{
            P: "Lcl Translation", "Lcl Translation", "", "A",{local_position[0]:.9g},{local_position[1]:.9g},{local_position[2]:.9g}
            P: "Lcl Rotation", "Lcl Rotation", "", "A",0,0,0
            P: "Lcl Scaling", "Lcl Scaling", "", "A",1,1,1
        }}
        Shading: T
        Culling: "CullingOff"
    }}''')
                bone_connections.append(f'    C: "OO",{bone_id},{parent_id}')
            bone_objects_text = '\n'.join(bone_objects)
            bone_connections_text = '\n'.join(bone_connections)
            bone_definition = (f'    ObjectType: "Model" {{ Count: {len(self.bones) + 1} }}'
                               if self.bones else '    ObjectType: "Model" { Count: 1 }')
            content = f'''; FBX 7.4.0 project file
FBXHeaderExtension:  {{
    FBXHeaderVersion: 1003
    FBXVersion: 7400
    Creator: "AI Generator 3D Model Scanner"
}}
GlobalSettings:  {{
    Version: 1000
    Properties70:  {{
        P: "UpAxis", "int", "Integer", "",1
        P: "UpAxisSign", "int", "Integer", "",1
        P: "FrontAxis", "int", "Integer", "",2
        P: "FrontAxisSign", "int", "Integer", "",-1
        P: "CoordAxis", "int", "Integer", "",0
        P: "CoordAxisSign", "int", "Integer", "",1
        P: "UnitScaleFactor", "double", "Number", "",1
    }}
}}
Definitions:  {{
    Version: 100
    Count: {2 + len(self.bones)}
    ObjectType: "Geometry" {{ Count: 1 }}
{bone_definition}
}}
Objects:  {{
    Geometry: 100000, "Geometry::ScannedMesh", "Mesh" {{
        Vertices: *{vertex_count} {{
            a: {vertex_values}
        }}
        PolygonVertexIndex: *{polygon_count} {{
            a: {polygon_values}
        }}
        GeometryVersion: 124
        Layer: 0 {{
            Version: 100
        }}
    }}
    Model: 100001, "Model::ScannedMesh", "Mesh" {{
        Version: 232
        Properties70:  {{
            P: "Lcl Translation", "Lcl Translation", "", "A",0,0,0
            P: "Lcl Rotation", "Lcl Rotation", "", "A",0,0,0
            P: "Lcl Scaling", "Lcl Scaling", "", "A",1,1,1
        }}
        Shading: T
        Culling: "CullingOff"
    }}
{bone_objects_text}
}}
Connections:  {{
    C: "OO",100000,100001
    C: "OO",100001,0
{bone_connections_text}
}}
'''
            with open(path, 'w', encoding='utf-8', newline='\n') as stream:
                stream.write(content)
            self.status.set(
                f'Exported FBX: {len(vertices):,} vertices, {len(faces):,} faces, '
                f'{len(self.bones):,} bones — {path}')
        except Exception as error:
            messagebox.showerror('Export FBX', str(error))


def open_model_scanner(parent, embedded=False, on_back=None):
    return BinaryMeshScanner(parent, embedded=embedded, on_back=on_back)
