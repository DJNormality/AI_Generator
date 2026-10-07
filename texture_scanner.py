"""Embedded raw texture finder for AI Generator."""

import io
import os
import struct
import threading
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk


SIGNATURES = {
    'PNG': b'\x89PNG\r\n\x1a\n',
    'JPEG': b'\xff\xd8\xff',
    'DDS': b'DDS ',
    'BMP': b'BM',
    'KTX': b'\xabKTX 11\xbb\r\n\x1a\n',
    'KTX2': b'\xabKTX 20\xbb\r\n\x1a\n',
    'PVR': b'PVR\x03',
}

EXTENSIONS = {'PNG': '.png', 'JPEG': '.jpg', 'DDS': '.dds', 'BMP': '.bmp',
              'KTX': '.ktx', 'KTX2': '.ktx2', 'PVR': '.pvr'}


def _size_text(value):
    number = float(max(0, value))
    for unit in ('B', 'KB', 'MB', 'GB'):
        if number < 1024 or unit == 'GB':
            return f'{number:.0f} {unit}' if unit == 'B' else f'{number:.1f} {unit}'
        number /= 1024


@dataclass
class TextureResult:
    kind: str
    offset: int
    size: int
    width: int = 0
    height: int = 0

    def label(self, number):
        dimensions = f'{self.width}×{self.height}' if self.width and self.height else 'unknown size'
        return (f'Texture {number:03d} | {self.kind} | Offset 0x{self.offset:08X} | '
                f'{dimensions} | {_size_text(self.size)}')


class TextureScanner:
    def __init__(self, parent, on_back=None):
        self.on_back = on_back
        self.window = ttk.Frame(parent, style='App.TFrame')
        self.window.pack(fill=tk.BOTH, expand=True)
        self.data = b''
        self.path = ''
        self.results = []
        self.scanning = False
        self.stop_event = threading.Event()
        self.preview_photo = None
        self._build_ui()

    def _build_ui(self):
        toolbar = ttk.Frame(self.window, padding=(10, 8, 10, 6))
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text='← Back to Home', command=self.request_back).pack(
            side=tk.LEFT, padx=(0, 8))
        self.path_var = tk.StringVar()
        ttk.Entry(toolbar, textvariable=self.path_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(toolbar, text='Open Any File', command=self.open_file).pack(
            side=tk.LEFT, padx=6)
        self.scan_button = ttk.Button(toolbar, text='Search Textures', command=self.start_scan)
        self.scan_button.pack(side=tk.LEFT)
        self.stop_button = ttk.Button(
            toolbar, text='Stop', command=self.stop_scan, state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=(6, 0))

        progress_row = ttk.Frame(self.window, padding=(10, 0, 10, 6))
        progress_row.pack(fill=tk.X)
        self.progress = tk.DoubleVar(value=0)
        self.progress_text = tk.StringVar(value='0%')
        self.results_text = tk.StringVar(value='Results: 0')
        ttk.Progressbar(progress_row, variable=self.progress, maximum=100,
                        style='Accent.Horizontal.TProgressbar').pack(
                            side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(progress_row, textvariable=self.progress_text, width=6).pack(
            side=tk.LEFT, padx=(8, 0))
        ttk.Label(progress_row, textvariable=self.results_text, width=16).pack(
            side=tk.LEFT, padx=(8, 0))

        body = ttk.Panedwindow(self.window, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))
        left = ttk.Frame(body, padding=6)
        right = ttk.Frame(body)
        body.add(left, weight=0)
        body.add(right, weight=1)

        list_frame = ttk.Frame(left)
        list_frame.pack(fill=tk.BOTH, expand=True)
        self.result_list = tk.Listbox(
            list_frame, width=62, height=18, bg='#0f172a', fg='white',
            exportselection=False)
        self.result_list.grid(row=0, column=0, sticky='nsew')
        scroll_y = ttk.Scrollbar(list_frame, orient='vertical', command=self.result_list.yview)
        scroll_y.grid(row=0, column=1, sticky='ns')
        scroll_x = ttk.Scrollbar(list_frame, orient='horizontal', command=self.result_list.xview)
        scroll_x.grid(row=1, column=0, sticky='ew')
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        self.result_list.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.result_list.bind('<<ListboxSelect>>', self.preview_selected)
        self.result_list.bind('<MouseWheel>', self._wheel)

        buttons = ttk.Frame(left)
        buttons.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(buttons, text='Extract Selected', command=self.extract_selected).pack(
            side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(buttons, text='Extract All', command=self.extract_all).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

        self.canvas = tk.Canvas(right, bg='#020617', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.status = tk.StringVar(value='Open any file type to search for embedded textures.')
        ttk.Label(self.window, textvariable=self.status).pack(
            fill=tk.X, padx=10, pady=(0, 8))

    def _wheel(self, event):
        self.result_list.yview_scroll(-3 if event.delta > 0 else 3, 'units')
        return 'break'

    def open_file(self):
        path = filedialog.askopenfilename(title='Select any file', filetypes=[('All files', '*.*')])
        if not path:
            return
        try:
            with open(path, 'rb') as stream:
                self.data = stream.read()
            self.path = path
            self.path_var.set(path)
            self.status.set(f'Loaded {_size_text(len(self.data))}. Choose Search Textures.')
        except Exception as error:
            messagebox.showerror('Open texture source', str(error))

    def start_scan(self):
        if not self.data:
            self.open_file()
        if not self.data or self.scanning:
            return
        self.scanning = True
        self.stop_event.clear()
        self.scan_button.configure(state='disabled')
        self.stop_button.configure(state='normal')
        self._set_progress(0, 0)
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def stop_scan(self):
        self.stop_event.set()
        self.stop_button.configure(state='disabled')
        self.status.set('Stopping texture search…')

    def _scan_worker(self):
        found = []
        for signature_number, (kind, signature) in enumerate(SIGNATURES.items(), 1):
            start = 0
            while not self.stop_event.is_set():
                offset = self.data.find(signature, start)
                if offset < 0:
                    break
                result = self._measure(kind, offset)
                if result and result.size > 0:
                    found.append(result)
                start = offset + max(1, len(signature))
            percent = signature_number / len(SIGNATURES) * 100
            self.window.after(0, lambda p=percent, n=len(found): self._set_progress(p, n))
            if self.stop_event.is_set():
                break
        found.sort(key=lambda item: item.offset)
        unique = []
        occupied = set()
        for item in found:
            key = (item.offset, item.kind)
            if key not in occupied:
                occupied.add(key)
                unique.append(item)
        stopped = self.stop_event.is_set()
        self.window.after(0, lambda: self._finish_scan(unique, stopped))

    def _measure(self, kind, offset):
        data = self.data
        try:
            if kind == 'PNG':
                width, height = struct.unpack_from('>II', data, offset + 16)
                end = data.find(b'IEND', offset + 24)
                size = end + 8 - offset if end >= 0 else len(data) - offset
            elif kind == 'JPEG':
                width = height = 0
                end = data.find(b'\xff\xd9', offset + 3)
                size = end + 2 - offset if end >= 0 else len(data) - offset
            elif kind == 'BMP':
                size = struct.unpack_from('<I', data, offset + 2)[0]
                width, height = struct.unpack_from('<ii', data, offset + 18)
                width, height = abs(width), abs(height)
            elif kind == 'DDS':
                height, width = struct.unpack_from('<II', data, offset + 12)
                next_offset = self._next_signature(offset + 4)
                size = next_offset - offset
            elif kind == 'KTX':
                width, height = struct.unpack_from('<II', data, offset + 36)
                size = self._next_signature(offset + 12) - offset
            elif kind == 'KTX2':
                width, height = struct.unpack_from('<II', data, offset + 20)
                size = self._next_signature(offset + 12) - offset
            else:
                height, width = struct.unpack_from('<II', data, offset + 24)
                size = self._next_signature(offset + 4) - offset
            size = min(max(0, size), len(data) - offset)
            if width > 262144 or height > 262144:
                width = height = 0
            return TextureResult(kind, offset, size, width, height)
        except (struct.error, ValueError):
            return None

    def _next_signature(self, start):
        offsets = [self.data.find(signature, start) for signature in SIGNATURES.values()]
        offsets = [value for value in offsets if value >= 0]
        return min(offsets) if offsets else len(self.data)

    def _set_progress(self, percent, count):
        self.progress.set(percent)
        self.progress_text.set(f'{percent:.0f}%')
        self.results_text.set(f'Results: {count:,}')

    def _finish_scan(self, results, stopped):
        self.scanning = False
        self.scan_button.configure(state='normal')
        self.stop_button.configure(state='disabled')
        self.results = results
        self.result_list.delete(0, tk.END)
        for number, result in enumerate(results, 1):
            self.result_list.insert(tk.END, result.label(number))
        self.results_text.set(f'Results: {len(results):,}')
        prefix = 'Stopped; kept' if stopped else 'Search complete:'
        self.status.set(f'{prefix} {len(results):,} texture results.')
        if results:
            self.result_list.selection_set(0)
            self.preview_selected()

    def preview_selected(self, _event=None):
        selected = self.result_list.curselection()
        if not selected:
            return
        result = self.results[selected[0]]
        payload = self.data[result.offset:result.offset + result.size]
        self.canvas.delete('all')
        try:
            from PIL import Image, ImageTk
            with Image.open(io.BytesIO(payload)) as opened:
                image = opened.convert('RGBA')
            width = max(100, self.canvas.winfo_width() - 30)
            height = max(100, self.canvas.winfo_height() - 30)
            image.thumbnail((width, height), getattr(Image, 'Resampling', Image).LANCZOS)
            self.preview_photo = ImageTk.PhotoImage(image)
            self.canvas.create_image(
                self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2,
                image=self.preview_photo)
        except Exception:
            self.canvas.create_text(
                self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2,
                text=(f'{result.kind} texture\n{result.width}×{result.height}\n'
                      f'{_size_text(result.size)}\nPreview codec unavailable'),
                fill='#e5e7eb', justify='center', font=('Segoe UI', 14))

    def _write_result(self, result, path):
        with open(path, 'wb') as stream:
            stream.write(self.data[result.offset:result.offset + result.size])

    def extract_selected(self):
        selected = self.result_list.curselection()
        if not selected:
            messagebox.showwarning('Extract texture', 'Select a texture result first.')
            return
        result = self.results[selected[0]]
        path = filedialog.asksaveasfilename(
            defaultextension=EXTENSIONS[result.kind],
            filetypes=[(result.kind, '*' + EXTENSIONS[result.kind]), ('All files', '*.*')])
        if path:
            try:
                self._write_result(result, path)
                self.status.set(f'Extracted texture: {path}')
            except Exception as error:
                messagebox.showerror('Extract texture', str(error))

    def extract_all(self):
        if not self.results:
            messagebox.showwarning('Extract textures', 'No texture results are available.')
            return
        folder = filedialog.askdirectory(title='Select texture output folder')
        if not folder:
            return
        try:
            stem = os.path.splitext(os.path.basename(self.path))[0] or 'texture'
            for number, result in enumerate(self.results, 1):
                name = f'{stem}_texture_{number:03d}{EXTENSIONS[result.kind]}'
                self._write_result(result, os.path.join(folder, name))
            self.status.set(f'Extracted {len(self.results):,} textures to {folder}')
        except Exception as error:
            messagebox.showerror('Extract textures', str(error))

    def request_back(self):
        if self.scanning:
            self.stop_event.set()
            self.window.after(75, self.request_back)
            return
        if self.on_back:
            self.on_back(self)


def open_texture_scanner(parent, on_back=None):
    return TextureScanner(parent, on_back=on_back)
