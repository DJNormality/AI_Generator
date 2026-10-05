import os
import cv2
import insightface
import onnxruntime
import numpy as np
import pickle
from moviepy import VideoFileClip, ImageSequenceClip
import requests
from tqdm import tqdm
import tkinter as tk
from tkinter import filedialog, scrolledtext, Toplevel, messagebox, ttk
import threading
import sys
import json
import time
import shutil
import hashlib
import webbrowser
import base64
from io import BytesIO
from types import SimpleNamespace
from insightface.utils import face_align


SWAPPER_MODELS = {
    'inswapper_128.onnx (Quality)': {
        'filename': 'inswapper_128.onnx',
        'url': 'https://huggingface.co/deepinsight/inswapper/resolve/main/inswapper_128.onnx',
        'input_size': 128,
    },
    'inswapper_128_fp16.onnx (Speed)': {
        'filename': 'inswapper_128_fp16.onnx',
        'url': 'https://huggingface.co/deepinsight/inswapper/resolve/main/inswapper_128_fp16.onnx',
        'input_size': 128,
    },
    'reswapper_256.onnx (256 Quality)': {
        'filename': 'reswapper_256.onnx',
        'url': (
            'https://huggingface.co/somanchiu/reswapper/resolve/'
            '2e410ffce5d3f4a2b94d852512160330f2325cdc/'
            'reswapper_256-1567500_originalInswapperClassCompatible.onnx'
        ),
        'input_size': 256,
    },
}

POST_PROCESS_MODELS = {
    'CodeFormer': {
        'filename': 'codeformer_fp16.onnx',
        'url': 'https://huggingface.co/OwlMaster/AllFilesRope/resolve/main/codeformer_fp16.onnx',
        'kind': 'face',
    },
    'GFPGAN 1024': {
        'filename': 'gfpgan-1024.onnx',
        'url': 'https://github.com/Glat0s/GFPGAN-1024-onnx/releases/download/v0.0.1/gfpgan-1024.onnx',
        'kind': 'face',
    },
    'RestoreFormer++': {
        'filename': 'RestoreFormerPlusPlus.fp16.onnx',
        'url': ('https://huggingface.co/OwlMaster/AllFilesRope/resolve/'
                '35eb4b3b905c7737494b65d464ef07d0f60364df/'
                'RestoreFormerPlusPlus.fp16.onnx'),
        'kind': 'face',
    },
    'GPEN 512': {
        'filename': 'GPEN-BFR-512.onnx',
        'url': ('https://huggingface.co/datasets/Gourieff/ReActor/resolve/main/'
                'models/facerestore_models/GPEN-BFR-512.onnx'),
        'kind': 'face',
    },
    'GPEN 1024': {
        'filename': 'GPEN-BFR-1024.onnx',
        'url': ('https://huggingface.co/datasets/Gourieff/ReActor/resolve/main/'
                'models/facerestore_models/GPEN-BFR-1024.onnx'),
        'kind': 'face',
    },
    'ColorizeStable': {
        'filename': 'ColorizeStable.fp16.onnx',
        'url': 'https://huggingface.co/OwlMaster/AllFilesRope/resolve/main/ColorizeStable.fp16.onnx',
        'kind': 'face',
    },
    'RealESRGAN x4': {
        'filename': 'RealESRGAN_x4plus.fp16.onnx',
        'url': ('https://huggingface.co/OwlMaster/AllFilesRope/resolve/'
                'd783e61585b3d83a85c91ca8a3b299e8ade94d72/'
                'RealESRGAN_x4plus.fp16.onnx'),
        'kind': 'upscale',
    },
    'UltraSharp 4x': {
        'filename': '4x-UltraSharp.fp16.onnx',
        'url': ('https://huggingface.co/OwlMaster/AllFilesRope/resolve/'
                '7d4e24beaef0e14215e1b3916a144f14ac9191d9/'
                '4x-UltraSharp.fp16.onnx'),
        'kind': 'upscale',
    },
    'UltraMix Smooth 4x': {
        'filename': '4x-UltraMix_Smooth.fp16.onnx',
        'url': ('https://huggingface.co/OwlMaster/AllFilesRope/resolve/main/'
                '4x-UltraMix_Smooth.fp16.onnx'),
        'kind': 'upscale',
    },
    'DDColor Natural': {
        'filename': 'ddcolor.onnx',
        'url': 'https://huggingface.co/facefusion/models-3.0.0/resolve/main/ddcolor.onnx',
        'kind': 'colorize',
    },
    'DDColor Artistic': {
        'filename': 'ddcolor_artistic.onnx',
        'url': 'https://huggingface.co/facefusion/models-3.0.0/resolve/main/ddcolor_artistic.onnx',
        'kind': 'colorize',
    },
    'Occluder': {
        'filename': 'occluder.onnx',
        'url': ('https://huggingface.co/OwlMaster/AllFilesRope/resolve/'
                'd783e61585b3d83a85c91ca8a3b299e8ade94d72/occluder.onnx'),
        'kind': 'mask',
    },
    'FaceParser': {
        'filename': 'faceparser_resnet34.onnx',
        'url': ('https://huggingface.co/MonsterMMORPG/Wan_GGUF/resolve/'
                '23e3e3db85947c1d1dc0f7e2e00529c8d5228293/'
                'Viso_Master_Models/faceparser_resnet34.onnx'),
        'kind': 'mask',
    },
    'XSeg': {
        'filename': 'XSeg_model.onnx',
        'url': ('https://huggingface.co/OwlMaster/AllFilesRope/resolve/'
                'd783e61585b3d83a85c91ca8a3b299e8ade94d72/XSeg_model.onnx'),
        'kind': 'mask',
    },
}


class RoundedButton(tk.Canvas):
    """Dependency-free rounded button used by the modern interface."""
    def __init__(self, parent, text, command=None, bg='#374151', hover='#4b5563',
                 fg='#ffffff', canvas_bg='#111827', radius=12, height=42, width=120,
                 state='normal', icon=None, image_path=None, image_size=30):
        super().__init__(parent, height=height, width=width, bg=canvas_bg,
                         highlightthickness=0, bd=0, cursor='hand2')
        self._text = text
        self._command = command
        self._normal_bg = bg
        self._hover_bg = hover
        self._fg = fg
        self._radius = radius
        self._state = state
        self._icon = icon
        self._button_image = None
        if image_path:
            try:
                from PIL import Image, ImageTk
                source_image = Image.open(image_path).convert('RGBA')
                source_image.thumbnail((image_size, image_size), Image.Resampling.LANCZOS)
                self._button_image = ImageTk.PhotoImage(source_image)
            except Exception:
                # Keep the built-in vector icon as a safe fallback.
                self._button_image = None
        self.bind('<Configure>', lambda event: self._draw())
        self.bind('<Enter>', lambda event: self._draw(self._hover_bg))
        self.bind('<Leave>', lambda event: self._draw())
        self.bind('<Button-1>', self._click)

    def _rounded_rectangle(self, x1, y1, x2, y2, radius, **kwargs):
        points = [x1 + radius, y1, x2 - radius, y1, x2, y1,
                  x2, y1 + radius, x2, y2 - radius, x2, y2,
                  x2 - radius, y2, x1 + radius, y2, x1, y2,
                  x1, y2 - radius, x1, y1 + radius, x1, y1]
        return self.create_polygon(points, smooth=True, splinesteps=24, **kwargs)

    def _draw(self, color=None):
        self.delete('all')
        width = max(2, self.winfo_width())
        height = max(2, self.winfo_height())
        disabled = self._state == 'disabled'
        fill = '#334155' if disabled else (color or self._normal_bg)
        text_color = '#94a3b8' if disabled else self._fg
        self._rounded_rectangle(1, 1, width - 1, height - 1,
                                min(self._radius, height // 2), fill=fill, outline='')
        if self._button_image:
            self.create_image(width // 2, height // 2, image=self._button_image)
        elif self._icon:
            self._draw_icon(self._icon, width // 2, height // 2, text_color)
        else:
            self.create_text(width // 2, height // 2, text=self._text,
                             fill=text_color, font=('Segoe UI Semibold', 10))
        super().configure(cursor='' if disabled else 'hand2')

    def _draw_icon(self, icon, cx, cy, color):
        if icon == 'patreon':
            self.create_rectangle(cx - 13, cy - 12, cx - 8, cy + 12,
                                  fill=color, outline='')
            self.create_oval(cx - 3, cy - 11, cx + 17, cy + 9,
                             fill=color, outline='')
        elif icon == 'discord':
            # Compact Discord controller mark.
            self.create_arc(cx - 17, cy - 11, cx + 17, cy + 15,
                            start=15, extent=150, style=tk.ARC,
                            outline=color, width=4)
            self.create_arc(cx - 17, cy - 11, cx + 17, cy + 15,
                            start=195, extent=150, style=tk.ARC,
                            outline=color, width=4)
            self.create_oval(cx - 9, cy - 2, cx - 5, cy + 2,
                             fill=color, outline='')
            self.create_oval(cx + 5, cy - 2, cx + 9, cy + 2,
                             fill=color, outline='')
        elif icon == 'paypal':
            self.create_text(cx - 3, cy, text='P', fill='#dbeafe',
                             font=('Segoe UI Black', 24))
            self.create_text(cx + 4, cy + 2, text='P', fill=color,
                             font=('Segoe UI Black', 21))

    def _click(self, _event):
        if self._state != 'disabled' and self._command:
            self._command()

    def config(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)
        if 'text' in kwargs:
            self._text = kwargs.pop('text')
        if 'command' in kwargs:
            self._command = kwargs.pop('command')
        if 'state' in kwargs:
            self._state = kwargs.pop('state')
        if kwargs:
            super().config(**kwargs)
        self._draw()

    configure = config

# ==============================================================================
# --- 1. GUI APPLICATION CLASS ---
# ==============================================================================

class FaceSwapApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Generator")
        # Load a replaceable app icon and keep the PNG object alive.
        app_dir = os.path.dirname(os.path.abspath(__file__))
        resources_dir = os.path.join(app_dir, 'resources')
        ico_path = os.path.join(resources_dir, 'AI_Generator.ico')
        png_path = os.path.join(resources_dir, 'AI_Generator.png')
        self._window_icon_image = None
        try:
            if sys.platform == 'win32' and os.path.exists(ico_path):
                self.root.iconbitmap(default=ico_path)
            if os.path.exists(png_path):
                self._window_icon_image = tk.PhotoImage(file=png_path)
                self.root.iconphoto(True, self._window_icon_image)
        except (tk.TclError, OSError):
            # Missing or invalid custom artwork should never prevent startup.
            self._window_icon_image = None
        self.root.geometry("900x720")
        self.root.minsize(820, 640)
        self.root.configure(bg='#111827')
        try:
            self.root.attributes('-alpha', 0.96)
        except tk.TclError:
            pass

        # --- State & Threading Variables ---
        self.is_processing = False
        self.is_paused = False
        self.is_resume_mode = False
        self.pause_event = threading.Event()
        self.stop_event = threading.Event()

        # --- UI Variables ---
        self.source_dir = tk.StringVar()
        self.target_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.temp_dir = tk.StringVar()
        self.models_dir = tk.StringVar(value='models')
        self.gpu_provider = tk.StringVar()
        self.swapper_model = tk.StringVar()
        self.enable_color_correction = tk.BooleanVar(value=True)
        self.processing_resolution = tk.StringVar()
        self.enable_quick_scan = tk.BooleanVar(value=True)
        self.enable_review_pass = tk.BooleanVar(value=True)
        self.enable_manual_review = tk.BooleanVar(value=False) # New var for manual review
        self.face_consistency = tk.StringVar()
        self.face_restorer = tk.StringVar()
        self.restoration_strength = tk.DoubleVar(value=0.7)
        self.restoration_percent = tk.StringVar(value='70%')
        self.restoration_strength.trace_add('write', self._update_restoration_percent)
        self.enable_colorize_model = tk.BooleanVar(value=False)
        self.upscale_factor = tk.StringVar()
        self.upscale_model = tk.StringVar()
        self.colorization_model = tk.StringVar()
        self.brightness = tk.DoubleVar(value=0.0)
        self.gamma = tk.DoubleVar(value=1.0)
        self.enable_smart_masking = tk.BooleanVar(value=False)
        self.enable_prompt_edit = tk.BooleanVar(value=False)
        self.prompt_engine = tk.StringVar(value='Local')
        self.cloud_image_model = tk.StringVar(value='gpt-image-2.5-sunburst')
        self.cloud_image_quality = tk.StringVar(value='high')
        self.qwen_image_model = tk.StringVar(value='Qwen/Qwen-Image-Edit')
        self.a2e_image_model = tk.StringVar(value='nano-banana-pro')
        self.a2e_resolution = tk.StringVar(value='2K')
        self.edit_prompt = tk.StringVar()
        self.negative_prompt = tk.StringVar()
        self.prompt_steps = tk.IntVar(value=20)
        self.prompt_for_videos = tk.BooleanVar(value=False)
        self.rebuild_face_index = tk.BooleanVar(value=False)
        self.reprocess_existing = tk.BooleanVar(value=False)
        self.crop_input_dir = tk.StringVar()
        self.crop_output_dir = tk.StringVar()
        self.crop_mode = tk.StringVar(value='Aspect ratio')
        self.crop_ratio = tk.StringVar(value='1:1')
        self.crop_width = tk.IntVar(value=1024)
        self.crop_height = tk.IntVar(value=1024)
        self.crop_overwrite = tk.BooleanVar(value=False)

        self.config_file = 'config.json'
        self.load_settings()

        self.configure_modern_styles()

        # --- Modern UI Layout ---
        main_frame = ttk.Frame(root, style='App.TFrame', padding=18)
        main_frame.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(main_frame, style='App.TFrame')
        header.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(header, text="AI GENERATOR", style='Title.TLabel').pack(anchor='w')
        ttk.Label(header, text="Face replacement, restoration, prompt editing and upscaling",
                  style='Subtitle.TLabel').pack(anchor='w', pady=(2, 0))

        notebook = ttk.Notebook(main_frame, style='Modern.TNotebook')
        notebook.pack(fill=tk.X, pady=(0, 12))
        paths_tab = ttk.Frame(notebook, style='Panel.TFrame', padding=16)
        swap_tab = ttk.Frame(notebook, style='Panel.TFrame', padding=16)
        enhance_tab = ttk.Frame(notebook, style='Panel.TFrame', padding=16)
        prompt_tab = ttk.Frame(notebook, style='Panel.TFrame', padding=16)
        crop_tab = ttk.Frame(notebook, style='Panel.TFrame', padding=16)
        notebook.add(paths_tab, text='  Paths  ')
        notebook.add(swap_tab, text='  Face Swap  ')
        notebook.add(enhance_tab, text='  Enhance  ')
        notebook.add(prompt_tab, text='  Prompt Edit  ')
        notebook.add(crop_tab, text='  Crop  ')
        self.create_modern_tabs(paths_tab, swap_tab, enhance_tab, prompt_tab, crop_tab)

        progress_frame = ttk.Frame(main_frame, style='App.TFrame')
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        progress_frame.grid_columnconfigure(1, weight=1)
        self.status_text = tk.StringVar(value='Ready')
        self.task_progress = tk.DoubleVar(value=0.0)
        self.overall_progress = tk.DoubleVar(value=0.0)
        self.task_percent_text = tk.StringVar(value='0%')
        self.overall_percent_text = tk.StringVar(value='0%')
        self.last_issue_text = tk.StringVar(value='')
        ttk.Label(progress_frame, text="Current task", style='Status.TLabel').grid(
            row=0, column=0, sticky='w', padx=(0, 12), pady=4)
        self.task_progress_bar = ttk.Progressbar(
            progress_frame, mode='determinate', maximum=100,
            variable=self.task_progress, style='Accent.Horizontal.TProgressbar')
        self.task_progress_bar.grid(row=0, column=1, sticky='ew', pady=4)
        ttk.Label(progress_frame, textvariable=self.task_percent_text,
                  style='Percent.TLabel', width=5).grid(row=0, column=2, padx=(10, 0))
        ttk.Label(progress_frame, text="Overall", style='Status.TLabel').grid(
            row=1, column=0, sticky='w', padx=(0, 12), pady=4)
        self.overall_progress_bar = ttk.Progressbar(
            progress_frame, mode='determinate', maximum=100,
            variable=self.overall_progress, style='Overall.Horizontal.TProgressbar')
        self.overall_progress_bar.grid(row=1, column=1, sticky='ew', pady=4)
        ttk.Label(progress_frame, textvariable=self.overall_percent_text,
                  style='Percent.TLabel', width=5).grid(row=1, column=2, padx=(10, 0))
        ttk.Label(progress_frame, textvariable=self.status_text,
                  style='HintStatus.TLabel').grid(row=2, column=0, columnspan=3, sticky='w', pady=(4, 0))
        ttk.Label(progress_frame, textvariable=self.last_issue_text,
                  style='HintStatus.TLabel', wraplength=820).grid(
                      row=3, column=0, columnspan=3, sticky='w', pady=(2, 0))

        control_frame = ttk.Frame(main_frame, style='App.TFrame')
        control_frame.pack(fill=tk.X, pady=(0, 12))
        self.create_control_buttons(control_frame)

        link_frame = ttk.Frame(main_frame, style='App.TFrame')
        link_frame.pack(fill=tk.X)
        support_group = ttk.Frame(link_frame, style='App.TFrame')
        support_group.pack(side=tk.RIGHT)
        asset_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')
        RoundedButton(support_group, text='', icon='patreon',
                      image_path=os.path.join(asset_root, 'Patreon.png'),
                      command=lambda: self.open_external_link('https://www.patreon.com/c/3dmodelserver'),
                      bg='#f96854', hover='#ff7b6b', width=54, height=46, radius=16).pack(side=tk.LEFT, padx=(0, 8))
        RoundedButton(support_group, text='', icon='discord',
                      image_path=os.path.join(asset_root, 'Discord.png'),
                      command=lambda: self.open_external_link('https://discord.com/invite/sMZuNzhmxC'),
                      bg='#5865f2', hover='#7289da', width=54, height=46, radius=16).pack(side=tk.LEFT, padx=8)
        RoundedButton(support_group, text='', icon='paypal',
                      image_path=os.path.join(asset_root, 'PayPal.png'),
                      command=lambda: self.open_external_link(
                          'https://www.paypal.com/paypalme/GameModNation?country.x=US&locale.x=en_US'),
                      bg='#0070ba', hover='#169bd7', width=54, height=46, radius=16).pack(side=tk.LEFT, padx=8)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.check_for_resume_state()
        self.root.after_idle(self.fit_window_to_screen)

    def fit_window_to_screen(self):
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        requested_w = max(900, self.root.winfo_reqwidth() + 16)
        requested_h = max(740, self.root.winfo_reqheight() + 24)
        width = min(requested_w, max(820, screen_w - 60))
        height = min(requested_h, max(640, screen_h - 40))
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2 - 10)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def configure_modern_styles(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10))
        style.configure('App.TFrame', background='#111827')
        style.configure('Panel.TFrame', background='#1f2937')
        style.configure('Title.TLabel', background='#111827', foreground='#f8fafc',
                        font=('Segoe UI Semibold', 20))
        style.configure('Subtitle.TLabel', background='#111827', foreground='#94a3b8')
        style.configure('Panel.TLabel', background='#1f2937', foreground='#e5e7eb')
        style.configure('Hint.TLabel', background='#1f2937', foreground='#94a3b8',
                        font=('Segoe UI', 9))
        style.configure('Status.TLabel', background='#111827', foreground='#60a5fa',
                        font=('Segoe UI Semibold', 10))
        style.configure('Percent.TLabel', background='#111827', foreground='#f8fafc',
                        font=('Segoe UI Semibold', 10), anchor='e')
        style.configure('HintStatus.TLabel', background='#111827', foreground='#94a3b8')
        style.configure('Modern.TNotebook', background='#111827', borderwidth=0)
        style.configure('Modern.TNotebook.Tab', background='#374151', foreground='#cbd5e1',
                        padding=(16, 9), borderwidth=0)
        style.map('Modern.TNotebook.Tab', background=[('selected', '#2563eb')],
                  foreground=[('selected', '#ffffff')])
        style.configure('Modern.TLabelframe', background='#111827', foreground='#cbd5e1')
        style.configure('Modern.TLabelframe.Label', background='#111827', foreground='#cbd5e1',
                        font=('Segoe UI Semibold', 10))
        style.configure('Modern.TEntry', fieldbackground='#0f172a', foreground='#f8fafc',
                        insertcolor='#ffffff', bordercolor='#475569', padding=8,
                        relief='flat', borderwidth=0)
        style.configure('Modern.TCombobox', fieldbackground='#0f172a', foreground='#f8fafc',
                        arrowcolor='#93c5fd', padding=7, relief='flat', borderwidth=0)
        style.map('Modern.TCombobox',
                  fieldbackground=[('readonly', '#0f172a')],
                  foreground=[('readonly', '#f8fafc')],
                  selectbackground=[('readonly', '#0f172a')],
                  selectforeground=[('readonly', '#f8fafc')])
        style.configure('Modern.TSpinbox', fieldbackground='#0f172a', foreground='#f8fafc',
                        arrowcolor='#93c5fd', padding=6)
        style.configure('Modern.TCheckbutton', background='#1f2937', foreground='#e5e7eb',
                        focuscolor='#1f2937', padding=4)
        style.map('Modern.TCheckbutton', background=[('active', '#1f2937')])
        style.configure('Accent.TButton', background='#2563eb', foreground='white',
                        padding=(14, 10), font=('Segoe UI Semibold', 10), borderwidth=0)
        style.map('Accent.TButton', background=[('active', '#3b82f6'), ('disabled', '#334155')])
        style.configure('Secondary.TButton', background='#374151', foreground='#e5e7eb',
                        padding=(12, 10), borderwidth=0)
        style.map('Secondary.TButton', background=[('active', '#4b5563')])
        style.configure('Danger.TButton', background='#dc2626', foreground='white',
                        padding=(12, 10), font=('Segoe UI Semibold', 10), borderwidth=0)
        style.map('Danger.TButton', background=[('active', '#ef4444'), ('disabled', '#4b3030')])
        style.configure('Accent.Horizontal.TProgressbar', troughcolor='#1f2937',
                        background='#22c55e', borderwidth=0)
        style.configure('Overall.Horizontal.TProgressbar', troughcolor='#1f2937',
                        background='#22c55e', borderwidth=0)

    def _tab_label(self, parent, text, row):
        ttk.Label(parent, text=text, style='Panel.TLabel').grid(
            row=row, column=0, sticky='w', padx=(0, 12), pady=6)

    def _tab_combo(self, parent, variable, values, row):
        widget = ttk.Combobox(parent, textvariable=variable, values=values,
                              state='readonly', style='Modern.TCombobox')
        widget.grid(row=row, column=1, sticky='ew', pady=6)
        return widget

    def create_modern_tabs(self, paths, swap, enhance, prompt, crop):
        for tab in (paths, swap, enhance, prompt, crop):
            tab.grid_columnconfigure(1, weight=1)

        self.create_path_entry(paths, "Source images", self.source_dir, self.browse_source_dir, 0)
        self.create_path_entry(paths, "Target media", self.target_dir, self.browse_target_dir, 1)
        self.create_path_entry(paths, "Output folder", self.output_dir, self.browse_output_dir, 2)
        self.create_path_entry(paths, "Temporary folder", self.temp_dir, self.browse_temp_dir, 3)

        self._tab_label(swap, "GPU provider", 0)
        self._tab_combo(swap, self.gpu_provider,
                        ['DmlExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider'], 0)
        self._tab_label(swap, "Swapper model", 1)
        self._tab_combo(swap, self.swapper_model, list(SWAPPER_MODELS.keys()), 1)
        self._tab_label(swap, "Processing resolution", 2)
        self._tab_combo(swap, self.processing_resolution, ['Original', '1280x720', '854x480'], 2)
        self._tab_label(swap, "Face consistency", 3)
        self._tab_combo(swap, self.face_consistency, ['Low', 'Medium', 'High', 'Maximum'], 3)
        checks = [
            ("Enable color correction", self.enable_color_correction),
            ("Enable quick scan", self.enable_quick_scan),
            ("Enable review pass", self.enable_review_pass),
            ("Enable manual review mode", self.enable_manual_review),
            ("Rebuild face index this run", self.rebuild_face_index),
            ("Reprocess existing outputs", self.reprocess_existing),
        ]
        for offset, (text, variable) in enumerate(checks, 4):
            ttk.Checkbutton(swap, text=text, variable=variable,
                            style='Modern.TCheckbutton').grid(
                row=offset, column=0, columnspan=2, sticky='w', pady=2)

        self._tab_label(enhance, "Face restoration", 0)
        self._tab_combo(enhance, self.face_restorer,
                        ['None', 'CodeFormer', 'GFPGAN 1024', 'RestoreFormer++',
                         'GPEN 512', 'GPEN 1024'], 0)
        self._tab_label(enhance, "Restoration strength", 1)
        restoration_row = ttk.Frame(enhance, style='Panel.TFrame')
        restoration_row.grid(row=1, column=1, sticky='ew', pady=6)
        restoration_row.grid_columnconfigure(0, weight=1)
        ttk.Scale(restoration_row, variable=self.restoration_strength, from_=0.0, to=1.0,
                  orient=tk.HORIZONTAL).grid(row=0, column=0, sticky='ew')
        ttk.Label(restoration_row, textvariable=self.restoration_percent,
                  style='Percent.TLabel', width=5, anchor='e').grid(
                      row=0, column=1, padx=(10, 0))
        self._tab_label(enhance, "Colorization", 2)
        self._tab_combo(enhance, self.colorization_model,
                        ['Off', 'ColorizeStable', 'DDColor Natural', 'DDColor Artistic'], 2)
        self._tab_label(enhance, "Upscale model", 3)
        self._tab_combo(enhance, self.upscale_model,
                        ['RealESRGAN', 'UltraSharp', 'UltraMix Smooth'], 3)
        self._tab_label(enhance, "Upscale factor", 4)
        self._tab_combo(enhance, self.upscale_factor, ['Off', '2x', '4x'], 4)
        self._tab_label(enhance, "Brightness (-100 to 100)", 5)
        ttk.Spinbox(enhance, textvariable=self.brightness, from_=-100, to=100,
                    increment=1, width=10).grid(row=5, column=1, sticky='w', pady=6)
        self._tab_label(enhance, "Gamma (0.20 to 3.00)", 6)
        ttk.Spinbox(enhance, textvariable=self.gamma, from_=0.2, to=3.0,
                    increment=0.05, width=10).grid(row=6, column=1, sticky='w', pady=6)
        ttk.Checkbutton(enhance, text="Smart occlusion and face-boundary protection",
                        variable=self.enable_smart_masking,
                        style='Modern.TCheckbutton').grid(
                            row=7, column=0, columnspan=2, sticky='w', pady=5)
        ttk.Label(enhance, text="Uses Occluder, FaceParser and XSeg together.",
                  style='Hint.TLabel').grid(row=8, column=0, columnspan=2, sticky='w', pady=(8, 0))

        ttk.Checkbutton(prompt, text="Enable prompt editing",
                        variable=self.enable_prompt_edit, style='Modern.TCheckbutton').grid(
            row=0, column=0, columnspan=2, sticky='w', pady=(0, 6))
        self._tab_label(prompt, "Prompt engine", 1)
        self._tab_combo(prompt, self.prompt_engine, ['A2E', 'Local', 'Cloud', 'Qwen Cloud'], 1)
        self._tab_label(prompt, "Cloud model", 2)
        self._tab_combo(prompt, self.cloud_image_model,
                        ['gpt-image-2.5-sunburst', 'gpt-image-2.5-flare'], 2)
        self._tab_label(prompt, "Cloud quality", 3)
        self._tab_combo(prompt, self.cloud_image_quality,
                        ['low', 'medium', 'high', 'xhigh', 'max'], 3)
        self._tab_label(prompt, "Qwen model", 4)
        self._tab_combo(prompt, self.qwen_image_model,
                        ['Qwen/Qwen-Image-Edit-2511', 'Qwen/Qwen-Image-Edit'], 4)
        self._tab_label(prompt, "A2E model", 5)
        self._tab_combo(prompt, self.a2e_image_model,
                        ['nano-banana-pro', 'nano-banana-2', 'nano-banana',
                         'nano-banana-2-lite',
                         'gpt-image-2.5-sunburst', 'gpt-image-2.5-flare',
                         'gpt-image-2', 'gpt-image-1.5',
                         'qwen-image-3.0-pro', 'qwen-image-3.0',
                         'qwen-image-2.0-pro', 'qwen-image-2.0'], 5)
        self._tab_label(prompt, "A2E resolution", 6)
        self._tab_combo(prompt, self.a2e_resolution, ['2K', '1K'], 6)
        ttk.Entry(prompt, textvariable=self.edit_prompt,
                  style='Modern.TEntry').grid(row=7, column=1, sticky='ew', pady=6)
        self._tab_label(prompt, "Edit prompt", 7)
        self._tab_label(prompt, "Negative prompt", 8)
        ttk.Entry(prompt, textvariable=self.negative_prompt,
                  style='Modern.TEntry').grid(row=8, column=1, sticky='ew', pady=6)
        self._tab_label(prompt, "Local / Qwen steps", 9)
        ttk.Spinbox(prompt, from_=10, to=50, textvariable=self.prompt_steps,
                    width=8, style='Modern.TSpinbox').grid(row=9, column=1, sticky='w', pady=6)
        ttk.Checkbutton(prompt, text="Apply to video frames (slow and may flicker)",
                        variable=self.prompt_for_videos, style='Modern.TCheckbutton').grid(
            row=10, column=0, columnspan=2, sticky='w', pady=6)
        ttk.Label(prompt, text="Example: give her straight hair, subtle makeup and glasses",
                  style='Hint.TLabel').grid(row=11, column=0, columnspan=2, sticky='w', pady=(8, 0))

        ttk.Label(crop, text="Manual crop", style='Panel.TLabel',
                  font=('Segoe UI Semibold', 11)).grid(
                      row=0, column=0, sticky='w', pady=(0, 6))
        ttk.Label(crop, text="Open one image, drag a crop box, preview it, and save a copy.",
                  style='Hint.TLabel').grid(row=0, column=1, sticky='w', pady=(0, 6))
        RoundedButton(crop, text="Open Manual Crop Editor", command=self.open_manual_crop_editor,
                      bg='#2563eb', hover='#3b82f6', width=240).grid(
                          row=1, column=0, columnspan=2, sticky='w', pady=(0, 14))

        ttk.Separator(crop, orient=tk.HORIZONTAL).grid(
            row=2, column=0, columnspan=3, sticky='ew', pady=(0, 12))
        ttk.Label(crop, text="Batch crop", style='Panel.TLabel',
                  font=('Segoe UI Semibold', 11)).grid(row=3, column=0, sticky='w', pady=(0, 4))
        self.create_path_entry(crop, "Input folder", self.crop_input_dir,
                               self.browse_crop_input_dir, 4)
        self.create_path_entry(crop, "Output folder", self.crop_output_dir,
                               self.browse_crop_output_dir, 5)
        self._tab_label(crop, "Crop mode", 6)
        self._tab_combo(crop, self.crop_mode, ['Aspect ratio', 'Exact size'], 6)
        self._tab_label(crop, "Aspect ratio", 7)
        self._tab_combo(crop, self.crop_ratio,
                        ['1:1', '4:5', '3:4', '2:3', '16:9', '9:16'], 7)
        exact_row = ttk.Frame(crop, style='Panel.TFrame')
        exact_row.grid(row=8, column=1, sticky='w', pady=6)
        ttk.Label(crop, text="Exact output size", style='Panel.TLabel').grid(
            row=8, column=0, sticky='w', padx=(0, 12), pady=6)
        ttk.Spinbox(exact_row, from_=16, to=8192, textvariable=self.crop_width,
                    width=8, style='Modern.TSpinbox').pack(side=tk.LEFT)
        ttk.Label(exact_row, text=' × ', style='Panel.TLabel').pack(side=tk.LEFT)
        ttk.Spinbox(exact_row, from_=16, to=8192, textvariable=self.crop_height,
                    width=8, style='Modern.TSpinbox').pack(side=tk.LEFT)
        ttk.Checkbutton(crop, text="Overwrite files that already exist",
                        variable=self.crop_overwrite, style='Modern.TCheckbutton').grid(
                            row=9, column=0, columnspan=2, sticky='w', pady=4)
        RoundedButton(crop, text="Run Batch Crop", command=self.run_batch_crop_thread,
                      bg='#16a34a', hover='#22c55e', width=210).grid(
                          row=10, column=0, columnspan=2, sticky='w', pady=(8, 0))

    def create_settings_widgets(self, parent):
        tk.Label(parent, text="GPU Provider:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        tk.OptionMenu(parent, self.gpu_provider, *['DmlExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']).grid(row=0, column=1, sticky='ew', padx=5)
        tk.Label(parent, text="Swapper Model:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        tk.OptionMenu(parent, self.swapper_model, *SWAPPER_MODELS.keys()).grid(row=1, column=1, sticky='ew', padx=5)
        tk.Checkbutton(parent, text="Enable Color Correction", variable=self.enable_color_correction).grid(row=2, column=0, sticky='w', padx=5, pady=2)
        tk.Label(parent, text="Processing Resolution:").grid(row=3, column=0, sticky='w', padx=5, pady=2)
        tk.OptionMenu(parent, self.processing_resolution, *['Original', '1280x720', '854x480']).grid(row=3, column=1, sticky='ew', padx=5)
        tk.Checkbutton(parent, text="Enable Quick Scan", variable=self.enable_quick_scan).grid(row=4, column=0, sticky='w', padx=5, pady=2)
        tk.Checkbutton(parent, text="Enable Review Pass", variable=self.enable_review_pass).grid(row=5, column=0, sticky='w', padx=5, pady=2)
        tk.Label(parent, text="Face Consistency:").grid(row=6, column=0, sticky='w', padx=5, pady=2)
        tk.OptionMenu(parent, self.face_consistency, *['Low', 'Medium', 'High', 'Maximum']).grid(row=6, column=1, sticky='ew', padx=5)
        tk.Checkbutton(parent, text="Enable Manual Review Mode", variable=self.enable_manual_review).grid(row=7, column=0, columnspan=2, sticky='w', padx=5, pady=2)
        tk.Label(parent, text="Face Restoration:").grid(row=8, column=0, sticky='w', padx=5, pady=2)
        tk.OptionMenu(parent, self.face_restorer, *['None', 'CodeFormer', 'GFPGAN 1024']).grid(row=8, column=1, sticky='ew', padx=5)
        tk.Label(parent, text="Restoration Strength:").grid(row=9, column=0, sticky='w', padx=5, pady=2)
        tk.Scale(parent, variable=self.restoration_strength, from_=0.0, to=1.0, resolution=0.05,
                 orient=tk.HORIZONTAL).grid(row=9, column=1, sticky='ew', padx=5)
        tk.Checkbutton(parent, text="Enable ColorizeStable", variable=self.enable_colorize_model).grid(row=10, column=0, columnspan=2, sticky='w', padx=5, pady=2)
        tk.Label(parent, text="RealESRGAN Upscale:").grid(row=11, column=0, sticky='w', padx=5, pady=2)
        tk.OptionMenu(parent, self.upscale_factor, *['Off', '2x', '4x']).grid(row=11, column=1, sticky='ew', padx=5)
        tk.Checkbutton(parent, text="Enable Local Prompt Editing (NVIDIA)",
                       variable=self.enable_prompt_edit).grid(row=12, column=0, columnspan=2, sticky='w', padx=5, pady=2)
        tk.Label(parent, text="Edit Prompt:").grid(row=13, column=0, sticky='w', padx=5, pady=2)
        tk.Entry(parent, textvariable=self.edit_prompt).grid(row=13, column=1, sticky='ew', padx=5)
        tk.Label(parent, text="Negative Prompt:").grid(row=14, column=0, sticky='w', padx=5, pady=2)
        tk.Entry(parent, textvariable=self.negative_prompt).grid(row=14, column=1, sticky='ew', padx=5)
        tk.Label(parent, text="Prompt Steps:").grid(row=15, column=0, sticky='w', padx=5, pady=2)
        tk.Spinbox(parent, from_=10, to=50, textvariable=self.prompt_steps, width=8).grid(row=15, column=1, sticky='w', padx=5)
        tk.Checkbutton(parent, text="Apply prompts to video frames (slow; may flicker)",
                       variable=self.prompt_for_videos).grid(row=16, column=0, columnspan=2, sticky='w', padx=5, pady=2)
        tk.Checkbutton(parent, text="Rebuild Face Index This Run",
                       variable=self.rebuild_face_index).grid(row=17, column=0, columnspan=2, sticky='w', padx=5, pady=2)

    def create_control_buttons(self, parent):
        self.run_button = RoundedButton(parent, text="Run Full Process",
                                        command=self.start_processing_thread,
                                        bg='#2563eb', hover='#3b82f6', width=280)
        self.run_button.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        self.create_video_button = RoundedButton(parent, text="Create Videos",
                                                 command=self.create_videos_from_temp_thread)
        self.create_video_button.pack(side=tk.LEFT, fill=tk.X, padx=(8,0))

        self.review_button = RoundedButton(parent, text="Review", command=self.open_review_window,
                                           width=100)
        self.review_button.pack(side=tk.LEFT, padx=(8,0))

        self.clear_temp_button = RoundedButton(parent, text="Clear Temp",
                                               command=self.clear_temp_folder_ui, width=110)
        self.clear_temp_button.pack(side=tk.LEFT, fill=tk.X, padx=(8,0))
        
        self.stop_button = RoundedButton(parent, text="Stop", command=self.stop_processing,
                                         state='disabled', bg='#dc2626', hover='#ef4444', width=100)
        self.stop_button.pack(side=tk.RIGHT, fill=tk.X, padx=(8,0))

    def on_closing(self):
        self.save_settings()
        self.stop_event.set()
        self.root.destroy()

    def save_settings(self):
        settings = {
            'settings_version': 2,
            'source_dir': self.source_dir.get(),'target_dir': self.target_dir.get(),
            'output_dir': self.output_dir.get(),'temp_dir': self.temp_dir.get(),
            'gpu_provider': self.gpu_provider.get(),'processing_resolution': self.processing_resolution.get(),
            'face_consistency': self.face_consistency.get(), 'swapper_model': self.swapper_model.get(),
            'enable_manual_review': self.enable_manual_review.get(),
            'face_restorer': self.face_restorer.get(),
            'restoration_strength': self.restoration_strength.get(),
            'enable_colorize_model': self.enable_colorize_model.get(),
            'upscale_factor': self.upscale_factor.get(),
            'upscale_model': self.upscale_model.get(),
            'colorization_model': self.colorization_model.get(),
            'brightness': self.brightness.get(),
            'gamma': self.gamma.get(),
            'enable_smart_masking': self.enable_smart_masking.get(),
            'enable_prompt_edit': self.enable_prompt_edit.get(),
            'prompt_engine': self.prompt_engine.get(),
            'cloud_image_model': self.cloud_image_model.get(),
            'cloud_image_quality': self.cloud_image_quality.get(),
            'qwen_image_model': self.qwen_image_model.get(),
            'a2e_image_model': self.a2e_image_model.get(),
            'a2e_resolution': self.a2e_resolution.get(),
            'edit_prompt': self.edit_prompt.get(),
            'negative_prompt': self.negative_prompt.get(),
            'prompt_steps': self.prompt_steps.get(),
            'prompt_for_videos': self.prompt_for_videos.get(),
            'reprocess_existing': self.reprocess_existing.get(),
            'crop_input_dir': self.crop_input_dir.get(),
            'crop_output_dir': self.crop_output_dir.get(),
            'crop_mode': self.crop_mode.get(),
            'crop_ratio': self.crop_ratio.get(),
            'crop_width': self.crop_width.get(),
            'crop_height': self.crop_height.get(),
            'crop_overwrite': self.crop_overwrite.get(),
        }
        with open(self.config_file, 'w') as f: json.dump(settings, f, indent=4)

    def load_settings(self):
        try:
            with open(self.config_file, 'r') as f: settings = json.load(f)
            self.source_dir.set(settings.get('source_dir', 'source_images'))
            self.target_dir.set(settings.get('target_dir', 'target_videos'))
            self.output_dir.set(settings.get('output_dir', 'output'))
            self.temp_dir.set(settings.get('temp_dir', 'temp_processing'))
            self.gpu_provider.set(settings.get('gpu_provider', 'DmlExecutionProvider'))
            self.processing_resolution.set(settings.get('processing_resolution', 'Original'))
            self.face_consistency.set(settings.get('face_consistency', 'Medium'))
            self.swapper_model.set(settings.get('swapper_model', 'inswapper_128.onnx (Quality)'))
            self.enable_manual_review.set(settings.get('enable_manual_review', False))
            self.face_restorer.set(settings.get('face_restorer', 'None'))
            self.restoration_strength.set(settings.get('restoration_strength', 0.7))
            self.enable_colorize_model.set(settings.get('enable_colorize_model', False))
            self.upscale_factor.set(settings.get('upscale_factor', 'Off'))
            self.upscale_model.set(settings.get('upscale_model', 'RealESRGAN'))
            default_colorizer = 'ColorizeStable' if settings.get('enable_colorize_model', False) else 'Off'
            self.colorization_model.set(settings.get('colorization_model', default_colorizer))
            self.brightness.set(settings.get('brightness', 0.0))
            self.gamma.set(settings.get('gamma', 1.0))
            self.enable_smart_masking.set(settings.get('enable_smart_masking', False))
            self.enable_prompt_edit.set(settings.get('enable_prompt_edit', False))
            self.prompt_engine.set(settings.get('prompt_engine', 'Local'))
            self.cloud_image_model.set(settings.get('cloud_image_model', 'gpt-image-2.5-sunburst'))
            self.cloud_image_quality.set(settings.get('cloud_image_quality', 'high'))
            self.qwen_image_model.set(settings.get('qwen_image_model', 'Qwen/Qwen-Image-Edit'))
            # Older installs saved Sunburst before Nano Banana became the
            # recommended A2E editor. Migrate that old default once, while
            # preserving any model choice made after this settings revision.
            saved_a2e_model = settings.get('a2e_image_model', 'nano-banana-pro')
            if settings.get('settings_version', 1) < 2 and saved_a2e_model == 'gpt-image-2.5-sunburst':
                saved_a2e_model = 'nano-banana-pro'
            self.a2e_image_model.set(saved_a2e_model)
            self.a2e_resolution.set(settings.get('a2e_resolution', '2K'))
            self.edit_prompt.set(settings.get('edit_prompt', ''))
            self.negative_prompt.set(settings.get('negative_prompt', 'blurry, distorted, deformed'))
            self.prompt_steps.set(settings.get('prompt_steps', 20))
            self.prompt_for_videos.set(settings.get('prompt_for_videos', False))
            self.reprocess_existing.set(settings.get('reprocess_existing', False))
            self.crop_input_dir.set(settings.get('crop_input_dir', ''))
            self.crop_output_dir.set(settings.get('crop_output_dir', ''))
            self.crop_mode.set(settings.get('crop_mode', 'Aspect ratio'))
            self.crop_ratio.set(settings.get('crop_ratio', '1:1'))
            self.crop_width.set(settings.get('crop_width', 1024))
            self.crop_height.set(settings.get('crop_height', 1024))
            self.crop_overwrite.set(settings.get('crop_overwrite', False))
        except (FileNotFoundError, json.JSONDecodeError):
            self.source_dir.set('source_images'); self.target_dir.set('target_videos')
            self.output_dir.set('output'); self.temp_dir.set('temp_processing')
            self.gpu_provider.set('DmlExecutionProvider'); self.processing_resolution.set('Original')
            self.face_consistency.set('Medium'); self.swapper_model.set('inswapper_128.onnx (Quality)')
            self.enable_manual_review.set(False)
            self.face_restorer.set('None'); self.restoration_strength.set(0.7)
            self.enable_colorize_model.set(False); self.upscale_factor.set('Off')
            self.upscale_model.set('RealESRGAN'); self.colorization_model.set('Off')
            self.brightness.set(0.0); self.gamma.set(1.0)
            self.enable_smart_masking.set(False)
            self.enable_prompt_edit.set(False); self.edit_prompt.set('')
            self.prompt_engine.set('Local')
            self.cloud_image_model.set('gpt-image-2.5-sunburst')
            self.cloud_image_quality.set('high')
            self.qwen_image_model.set('Qwen/Qwen-Image-Edit')
            self.a2e_image_model.set('nano-banana-pro')
            self.a2e_resolution.set('2K')
            self.negative_prompt.set('blurry, distorted, deformed')
            self.prompt_steps.set(20); self.prompt_for_videos.set(False)
            self.reprocess_existing.set(False)
            self.crop_input_dir.set(''); self.crop_output_dir.set('')
            self.crop_mode.set('Aspect ratio'); self.crop_ratio.set('1:1')
            self.crop_width.set(1024); self.crop_height.set(1024)
            self.crop_overwrite.set(False)

    def create_path_entry(self, parent, label_text, string_var, command, row):
        ttk.Label(parent, text=label_text, style='Panel.TLabel').grid(
            row=row, column=0, sticky='w', padx=(0, 12), pady=7)
        entry = ttk.Entry(parent, textvariable=string_var, style='Modern.TEntry')
        entry.grid(row=row, column=1, sticky='ew', pady=7)
        RoundedButton(parent, text="Browse", command=command, canvas_bg='#1f2937',
                      height=38, width=105, radius=11).grid(
                          row=row, column=2, padx=(10, 0), pady=7, sticky='ew')
        parent.grid_columnconfigure(1, weight=1)

    def browse_source_dir(self):
        dir_path = filedialog.askdirectory(initialdir=self.source_dir.get(), title="Select Source Images Folder")
        if dir_path: self.source_dir.set(dir_path)

    def browse_target_dir(self):
        dir_path = filedialog.askdirectory(initialdir=self.target_dir.get(), title="Select Target Media Folder")
        if dir_path: self.target_dir.set(dir_path)

    def browse_output_dir(self):
        dir_path = filedialog.askdirectory(initialdir=self.output_dir.get(), title="Select Output Folder")
        if dir_path: self.output_dir.set(dir_path)
        
    def browse_temp_dir(self):
        dir_path = filedialog.askdirectory(initialdir=self.temp_dir.get(), title="Select Temporary Processing Folder")
        if dir_path: self.temp_dir.set(dir_path)

    def browse_crop_input_dir(self):
        path = filedialog.askdirectory(
            initialdir=self.crop_input_dir.get() or self.target_dir.get(),
            title="Select Images to Batch Crop")
        if path:
            self.crop_input_dir.set(path)
            if not self.crop_output_dir.get():
                self.crop_output_dir.set(os.path.join(path, 'cropped'))

    def browse_crop_output_dir(self):
        path = filedialog.askdirectory(
            initialdir=self.crop_output_dir.get() or self.output_dir.get(),
            title="Select Cropped Image Output Folder")
        if path:
            self.crop_output_dir.set(path)

    def open_manual_crop_editor(self):
        image_path = filedialog.askopenfilename(
            title="Open Image to Crop",
            filetypes=[('Image files', '*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff'),
                       ('All files', '*.*')])
        if not image_path:
            return
        try:
            from PIL import Image, ImageOps, ImageTk
            source_image = ImageOps.exif_transpose(Image.open(image_path)).copy()
        except Exception as e:
            messagebox.showerror('Could not open image', str(e))
            return

        editor = Toplevel(self.root)
        editor.title('Manual Crop Editor')
        editor.geometry('900x700')
        editor.minsize(680, 520)
        editor.configure(bg='#111827')
        editor.transient(self.root)

        toolbar = ttk.Frame(editor, style='App.TFrame', padding=(12, 10))
        toolbar.pack(fill=tk.X)
        crop_info = tk.StringVar(value='Drag over the image to select a crop area.')
        ttk.Label(toolbar, textvariable=crop_info, style='Status.TLabel').pack(side=tk.LEFT)
        canvas = tk.Canvas(editor, bg='#020617', highlightthickness=0, cursor='crosshair')
        canvas.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))
        buttons = ttk.Frame(editor, style='App.TFrame', padding=(12, 0, 12, 12))
        buttons.pack(fill=tk.X)

        state = {'photo': None, 'scale': 1.0, 'offset_x': 0, 'offset_y': 0,
                 'start': None, 'rect': None, 'selection': None}

        def redraw(_event=None):
            canvas.delete('all')
            cw = max(1, canvas.winfo_width())
            ch = max(1, canvas.winfo_height())
            iw, ih = source_image.size
            scale = min(cw / iw, ch / ih, 1.0)
            dw, dh = max(1, int(iw * scale)), max(1, int(ih * scale))
            ox, oy = (cw - dw) // 2, (ch - dh) // 2
            resampling = getattr(Image, 'Resampling', Image).LANCZOS
            preview = source_image.resize((dw, dh), resampling)
            state['photo'] = ImageTk.PhotoImage(preview)
            state.update(scale=scale, offset_x=ox, offset_y=oy)
            canvas.create_image(ox, oy, image=state['photo'], anchor='nw', tags='image')
            state['selection'] = None
            state['rect'] = None
            crop_info.set(f'Image: {iw} × {ih} px — drag to select a crop area.')

        def clamp_point(x, y):
            iw, ih = source_image.size
            left, top = state['offset_x'], state['offset_y']
            right = left + iw * state['scale']
            bottom = top + ih * state['scale']
            return max(left, min(x, right)), max(top, min(y, bottom))

        def drag_start(event):
            state['start'] = clamp_point(event.x, event.y)
            if state['rect']:
                canvas.delete(state['rect'])
            x, y = state['start']
            state['rect'] = canvas.create_rectangle(
                x, y, x, y, outline='#22c55e', width=3, dash=(7, 4))

        def drag_move(event):
            if state['start'] is None or state['rect'] is None:
                return
            x, y = clamp_point(event.x, event.y)
            canvas.coords(state['rect'], state['start'][0], state['start'][1], x, y)

        def drag_end(event):
            if state['start'] is None:
                return
            end = clamp_point(event.x, event.y)
            x1, x2 = sorted((state['start'][0], end[0]))
            y1, y2 = sorted((state['start'][1], end[1]))
            scale = state['scale']
            ox, oy = state['offset_x'], state['offset_y']
            box = (int(round((x1 - ox) / scale)), int(round((y1 - oy) / scale)),
                   int(round((x2 - ox) / scale)), int(round((y2 - oy) / scale)))
            iw, ih = source_image.size
            box = (max(0, min(iw, box[0])), max(0, min(ih, box[1])),
                   max(0, min(iw, box[2])), max(0, min(ih, box[3])))
            state['start'] = None
            if box[2] - box[0] < 2 or box[3] - box[1] < 2:
                state['selection'] = None
                crop_info.set('Selection is too small. Drag a larger crop area.')
                return
            state['selection'] = box
            crop_info.set(
                f'Crop: {box[2] - box[0]} × {box[3] - box[1]} px '
                f'at ({box[0]}, {box[1]})')

        def save_crop():
            box = state['selection']
            if not box:
                messagebox.showwarning('No crop selected', 'Drag a crop rectangle first.', parent=editor)
                return
            stem, extension = os.path.splitext(os.path.basename(image_path))
            save_path = filedialog.asksaveasfilename(
                parent=editor, title='Save Cropped Image',
                initialdir=os.path.dirname(image_path),
                initialfile=f'{stem}_cropped{extension}',
                defaultextension=extension or '.png',
                filetypes=[('PNG', '*.png'), ('JPEG', '*.jpg *.jpeg'),
                           ('WebP', '*.webp'), ('All files', '*.*')])
            if not save_path:
                return
            try:
                cropped = source_image.crop(box)
                if os.path.splitext(save_path)[1].lower() in ('.jpg', '.jpeg') and cropped.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', cropped.size, 'white')
                    if cropped.mode in ('RGBA', 'LA'):
                        background.paste(cropped, mask=cropped.getchannel('A'))
                    else:
                        background.paste(cropped.convert('RGBA'), mask=cropped.convert('RGBA').getchannel('A'))
                    cropped = background
                save_options = {'quality': 95} if os.path.splitext(save_path)[1].lower() in (
                    '.jpg', '.jpeg', '.webp') else {}
                cropped.save(save_path, **save_options)
                crop_info.set(f'Saved: {save_path}')
                messagebox.showinfo('Crop saved', save_path, parent=editor)
            except Exception as e:
                messagebox.showerror('Could not save crop', str(e), parent=editor)

        canvas.bind('<ButtonPress-1>', drag_start)
        canvas.bind('<B1-Motion>', drag_move)
        canvas.bind('<ButtonRelease-1>', drag_end)
        canvas.bind('<Configure>', redraw)
        RoundedButton(buttons, text='Save Crop', command=save_crop,
                      bg='#16a34a', hover='#22c55e', width=150).pack(side=tk.RIGHT)
        RoundedButton(buttons, text='Reset Selection', command=redraw,
                      width=150).pack(side=tk.RIGHT, padx=(0, 8))
        editor.after_idle(redraw)

    @staticmethod
    def _center_crop_box(image_width, image_height, target_ratio):
        current_ratio = image_width / image_height
        if current_ratio > target_ratio:
            crop_height = image_height
            crop_width = int(round(crop_height * target_ratio))
        else:
            crop_width = image_width
            crop_height = int(round(crop_width / target_ratio))
        left = max(0, (image_width - crop_width) // 2)
        top = max(0, (image_height - crop_height) // 2)
        return left, top, left + crop_width, top + crop_height

    def run_batch_crop_thread(self):
        threading.Thread(target=self._run_batch_crop, daemon=True).start()

    def _run_batch_crop(self):
        input_dir = self.crop_input_dir.get().strip()
        output_dir = self.crop_output_dir.get().strip()
        if not input_dir or not os.path.isdir(input_dir):
            self.root.after(0, lambda: messagebox.showerror(
                'Batch crop', 'Select a valid input folder.'))
            return
        if not output_dir:
            self.root.after(0, lambda: messagebox.showerror(
                'Batch crop', 'Select an output folder.'))
            return
        try:
            from PIL import Image, ImageOps
            mode = self.crop_mode.get()
            if mode == 'Exact size':
                out_width = max(16, int(self.crop_width.get()))
                out_height = max(16, int(self.crop_height.get()))
                ratio = out_width / out_height
            else:
                ratio_parts = self.crop_ratio.get().split(':')
                ratio = float(ratio_parts[0]) / float(ratio_parts[1])
                out_width = out_height = None
        except Exception as e:
            self.root.after(0, lambda err=str(e): messagebox.showerror(
                'Batch crop settings', err))
            return

        extensions = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff')
        files = sorted(name for name in os.listdir(input_dir) if name.lower().endswith(extensions))
        if not files:
            self.root.after(0, lambda: messagebox.showinfo(
                'Batch crop', 'No supported images were found.'))
            return
        os.makedirs(output_dir, exist_ok=True)
        completed = skipped = failed = 0
        self.last_issue_text.set('')
        self.update_task_progress(0, f'Batch cropping {len(files)} images')
        resampling = getattr(Image, 'Resampling', Image).LANCZOS
        for index, filename in enumerate(files, 1):
            source_path = os.path.join(input_dir, filename)
            destination_path = os.path.join(output_dir, filename)
            if os.path.exists(destination_path) and not self.crop_overwrite.get():
                skipped += 1
            else:
                try:
                    with Image.open(source_path) as opened:
                        image = ImageOps.exif_transpose(opened).copy()
                    cropped = image.crop(self._center_crop_box(*image.size, ratio))
                    if mode == 'Exact size':
                        cropped = cropped.resize((out_width, out_height), resampling)
                    if os.path.splitext(destination_path)[1].lower() in ('.jpg', '.jpeg') and cropped.mode != 'RGB':
                        if cropped.mode in ('RGBA', 'LA'):
                            background = Image.new('RGB', cropped.size, 'white')
                            background.paste(cropped, mask=cropped.getchannel('A'))
                            cropped = background
                        else:
                            cropped = cropped.convert('RGB')
                    save_options = {'quality': 95} if os.path.splitext(destination_path)[1].lower() in (
                        '.jpg', '.jpeg', '.webp') else {}
                    cropped.save(destination_path, **save_options)
                    completed += 1
                except Exception as e:
                    failed += 1
                    self.log(f'Warning: could not crop {filename}: {e}')
            self.update_task_progress(index / len(files) * 100,
                                      f'Batch crop {index} of {len(files)}')
        summary = f'Batch crop complete: {completed} saved, {skipped} skipped, {failed} failed.'
        self.status_text.set(summary)
        self.root.after(0, lambda text=summary: messagebox.showinfo('Batch crop complete', text))

    def open_external_link(self, url):
        try:
            webbrowser.open_new_tab(url)
        except Exception as e:
            messagebox.showerror('Could not open link', str(e))

    def _update_restoration_percent(self, *_):
        try:
            value = max(0.0, min(1.0, float(self.restoration_strength.get())))
        except (tk.TclError, ValueError, TypeError):
            value = 0.0
        self.restoration_percent.set(f'{value * 100:.0f}%')

    def log(self, message):
        if sys.stdout is not None:
            print(message)
        clean = str(message).strip().split('\n')[-1].strip('- ').strip()
        if clean:
            self.status_text.set(clean[:120])
            lowered = clean.lower()
            if ('warning:' in lowered or 'error:' in lowered or
                    'skipping:' in lowered or 'was disabled:' in lowered):
                self.last_issue_text.set(f'Last issue: {clean[:500]}')
        self.root.update_idletasks()

    def update_task_progress(self, value, label=None):
        value = max(0.0, min(100.0, float(value)))
        self.task_progress.set(value)
        self.task_percent_text.set(f'{value:.0f}%')
        if label:
            self.status_text.set(label)
        self.root.update_idletasks()

    def update_overall_progress(self, value, label=None):
        value = max(0.0, min(100.0, float(value)))
        self.overall_progress.set(value)
        self.overall_percent_text.set(f'{value:.0f}%')
        if label:
            self.status_text.set(label)
        self.root.update_idletasks()

    def start_processing_thread(self):
        self.is_processing = True
        self.stop_event.clear()
        self.pause_event.clear()
        self.run_button.config(text="Pause", command=self.toggle_pause)
        self.stop_button.config(state='normal')
        self.status_text.set('Processing…')
        self.last_issue_text.set('')
        self.update_task_progress(0)
        self.update_overall_progress(0)
        self.processing_thread = threading.Thread(target=self.run_full_pipeline, args=(self.is_resume_mode,))
        self.processing_thread.start()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_event.set()
            self.run_button.config(text="Resume")
            self.log("...Pausing process. Click Resume to continue...")
            self.status_text.set('Paused')
        else:
            self.pause_event.clear()
            self.run_button.config(text="Pause")
            self.log("...Resuming process...")
            self.status_text.set('Processing…')

    def stop_processing(self):
        if self.is_processing:
            self.log("--- STOPPING PROCESS ---")
            self.stop_event.set()
            self.status_text.set('Stopping…')
            if self.is_paused: self.pause_event.clear()
    
    def clear_temp_folder_ui(self):
        config = self.get_config_from_ui()
        temp_path = config['TEMP_DIR']
        if not os.path.exists(temp_path) or not os.listdir(temp_path):
            self.log("Temp folder is already empty.")
            return
        
        total_size = sum(os.path.getsize(os.path.join(dirpath, filename)) for dirpath, _, filenames in os.walk(temp_path) for filename in filenames)
        size_gb = total_size / (1024**3)
        
        if messagebox.askyesno("Confirm Clear", f"The temporary folder is {size_gb:.2f} GB. Are you sure you want to clear it? This cannot be undone."):
            self.log("--- Manual Cleanup ---")
            cleanup_temp_folder(config, self.log)
            self.check_for_resume_state()

    def check_for_resume_state(self):
        temp_path = self.temp_dir.get()
        if os.path.exists(temp_path) and any(d.endswith('_frames') for d in os.listdir(temp_path)):
            self.is_resume_mode = True
            self.run_button.config(text="Resume Interrupted Process")
            self.log("Detected frames from a previous session. Ready to resume.")
        else:
            self.is_resume_mode = False
            self.run_button.config(text="Run Full Process")

    def reset_ui_state(self):
        self.is_processing = False
        self.is_paused = False
        self.run_button.config(text="Run Full Process", command=self.start_processing_thread)
        self.stop_button.config(state='disabled')
        self.status_text.set('Ready')
        self.check_for_resume_state()

    def open_review_window(self):
        ImageReviewer(self.root, self.get_config_from_ui(), self.log)

    def create_videos_from_temp_thread(self):
        threading.Thread(target=self.create_videos_from_temp).start()

    def create_videos_from_temp(self):
        self.log("\n--- Creating all videos from Temp folder ---")
        config = self.get_config_from_ui()
        temp_dir = config['TEMP_DIR']
        
        subfolders = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d)) and d.endswith('_swapped_frames')]
        if not subfolders:
            self.log("No completed swapped frame folders found in Temp.")
            return

        for folder in subfolders:
            try:
                # Reconstruct config for this specific video
                video_config = config.copy()
                parts = folder.replace('_swapped_frames', '').split('-')
                source_folder_name = parts[-1]
                video_name_part = '-'.join(parts[:-1])
                
                # Find original video file
                original_video_file = None
                for ext in ['.mp4', '.mov', '.avi', '.mkv']:
                    path_to_check = os.path.join(config['TARGET_DIR'], f"{video_name_part}{ext}")
                    if os.path.exists(path_to_check):
                        original_video_file = f"{video_name_part}{ext}"
                        break
                
                if not original_video_file:
                    self.log(f"Could not find original video for {folder}. Skipping.")
                    continue

                video_config['TARGET_VIDEO_PATH'] = os.path.join(config['TARGET_DIR'], original_video_file)
                video_config['FINAL_VIDEO_PATH'] = os.path.join(config['OUTPUT_DIR'], f"{video_name_part}-{source_folder_name}_swapped.mp4")
                video_config['SWAPPED_FRAMES_DIR'] = os.path.join(temp_dir, folder)

                self.log(f"--> Creating video for: {video_name_part}")
                step_4_create_final_video(video_config, self.log)
                cleanup_temp_folder(video_config, self.log, is_manual=True)
            except Exception as e:
                self.log(f"Error creating video from {folder}: {e}")
        
        self.log("--- Finished creating videos from Temp. ---")


    def run_full_pipeline(self, is_resume):
        try:
            base_config = self.get_config_from_ui()
            self.log("=============================================")
            self.log(f"=== STARTING PROCESS (Resume Mode: {is_resume}) ===")
            self.log("=============================================")

            setup_project_structure(base_config)
            download_swapper_model(base_config, self.log)
            download_post_process_models(base_config, self.log)
            
            if not is_resume:
                step_2_index_source_faces(base_config, self.log)
                self.rebuild_face_index.set(False)

            media_files = [f for f in os.listdir(base_config['TARGET_DIR']) if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.jpg', '.jpeg', '.png'))]
            if not media_files: raise Exception(f"No media files found in {base_config['TARGET_DIR']}.")
            
            total_media = len(media_files)
            self.log(f"Found {total_media} media file(s) to process.")
            self.update_overall_progress(0, f'Ready to process {total_media} files')

            for i, media_file in enumerate(media_files):
                if self.stop_event.is_set(): break
                
                self.log(f"\n--- Processing file {i+1} of {total_media}: {media_file} ---")
                self.update_task_progress(0, f'Generating {media_file}')
                
                file_ext = os.path.splitext(media_file)[1].lower()
                is_video = file_ext in ['.mp4', '.mov', '.avi', '.mkv']
                
                if is_video:
                    process_video(base_config, media_file, self.log, self.pause_event, self.stop_event, is_resume)
                else:
                    process_image(base_config, media_file, self.log)
                self.update_task_progress(100, f'Completed {media_file}')
                self.update_overall_progress(
                    (i + 1) / total_media * 100,
                    f'Completed {i + 1} of {total_media} files')
                
                is_resume = False

            if self.stop_event.is_set(): self.log("\n--- Process stopped by user. ---")
            else: self.log("\n--- All tasks completed successfully! ---")

        except Exception as e:
            self.log(f"\n--- AN ERROR OCCURRED ---\nError: {e}")
        finally:
            self.reset_ui_state()

    def get_config_from_ui(self):
        model_choice = self.swapper_model.get()
        model_info = SWAPPER_MODELS.get(model_choice)
        if model_info is None:
            # Preserve compatibility with older config.json values that contain
            # only a model filename or a now-unknown display label.
            model_filename = model_choice.split(' ')[0]
            expected_swapper_size = None
        else:
            model_filename = model_info['filename']
            expected_swapper_size = model_info['input_size']
        source_dir = self.source_dir.get()
        source_key = hashlib.sha256(os.path.abspath(source_dir).encode('utf-8')).hexdigest()[:16]
        return {
            'SOURCE_IMAGES_DIR': self.source_dir.get(), 'TARGET_DIR': self.target_dir.get(),
            'OUTPUT_DIR': self.output_dir.get(), 'TEMP_DIR': self.temp_dir.get(),
            'MODELS_DIR': self.models_dir.get(), 'GPU_PROVIDER': self.gpu_provider.get(),
            'ENABLE_COLOR_CORRECTION': self.enable_color_correction.get(),
            'ENABLE_QUICK_SCAN': self.enable_quick_scan.get(),
            'ENABLE_REVIEW_PASS': self.enable_review_pass.get(),
            'ENABLE_MANUAL_REVIEW': self.enable_manual_review.get(),
            'PROCESSING_RESOLUTION': self.processing_resolution.get(),
            'FACE_CONSISTENCY': self.face_consistency.get(),
            'FRAMES_PER_SECOND_TO_SAVE': 15,
            'INDEX_FILE_PATH': os.path.join(self.temp_dir.get(), 'source_faces_index.pkl'),
            'SWAPPER_MODEL_PATH': os.path.join(self.models_dir.get(), model_filename),
            'SWAPPER_MODEL_CHOICE': model_choice,
            'EXPECTED_SWAPPER_SIZE': expected_swapper_size,
            'FACE_RESTORER': self.face_restorer.get(),
            'RESTORATION_STRENGTH': self.restoration_strength.get(),
            'ENABLE_COLORIZE_MODEL': self.enable_colorize_model.get(),
            'UPSCALE_FACTOR': self.upscale_factor.get(),
            'UPSCALE_MODEL': self.upscale_model.get(),
            'COLORIZATION_MODEL': self.colorization_model.get(),
            'BRIGHTNESS': max(-100.0, min(100.0, self.brightness.get())),
            'GAMMA': max(0.2, min(3.0, self.gamma.get())),
            'ENABLE_SMART_MASKING': self.enable_smart_masking.get(),
            'ENABLE_PROMPT_EDIT': self.enable_prompt_edit.get(),
            'PROMPT_ENGINE': self.prompt_engine.get(),
            'CLOUD_IMAGE_MODEL': self.cloud_image_model.get(),
            'CLOUD_IMAGE_QUALITY': self.cloud_image_quality.get(),
            'QWEN_IMAGE_MODEL': self.qwen_image_model.get(),
            'A2E_IMAGE_MODEL': self.a2e_image_model.get(),
            'A2E_RESOLUTION': self.a2e_resolution.get(),
            'EDIT_PROMPT': self.edit_prompt.get().strip(),
            'NEGATIVE_PROMPT': self.negative_prompt.get().strip(),
            'PROMPT_STEPS': max(10, min(50, self.prompt_steps.get())),
            'PROMPT_FOR_VIDEOS': self.prompt_for_videos.get(),
            'REPROCESS_EXISTING': self.reprocess_existing.get(),
            'FORCE_REBUILD_INDEX': self.rebuild_face_index.get(),
            'PERSISTENT_INDEX_PATH': os.path.join(
                self.models_dir.get(), f'source_faces_{source_key}.pkl'),
            'TASK_PROGRESS_CALLBACK': self.update_task_progress,
            'OVERALL_PROGRESS_CALLBACK': self.update_overall_progress,
        }

# ==============================================================================
# --- 2. IMAGE REVIEWER CLASS ---
# ==============================================================================
class ImageReviewer(Toplevel):
    def __init__(self, parent, config, log_callback):
        super().__init__(parent)
        self.title("Image Review and Correction")
        self.geometry("600x400")
        self.config = config
        self.log = log_callback
        
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="Use this tool to find and fix frames that were missed by the automated process.").pack(pady=5)
        
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(btn_frame, text="1. Identify Unswapped Frames", command=self.identify_unswapped).pack(fill=tk.X, pady=2)
        tk.Button(btn_frame, text="2. Re-Swap Unswapped Frames", command=self.reswap_unswapped).pack(fill=tk.X, pady=2)
        
        self.log_text_review = scrolledtext.ScrolledText(main_frame, state='disabled', wrap=tk.WORD, height=10)
        self.log_text_review.pack(fill=tk.BOTH, expand=True)

    def review_log(self, message):
        self.log_text_review.config(state='normal')
        self.log_text_review.insert(tk.END, message + '\n')
        self.log_text_review.see(tk.END)
        self.log_text_review.config(state='disabled')

    def identify_unswapped(self):
        threading.Thread(target=self._identify_unswapped_thread).start()

    def _identify_unswapped_thread(self):
        self.review_log("--- Starting Identification Process ---")
        temp_dir = self.config['TEMP_DIR']
        swapped_folders = [d for d in os.listdir(temp_dir) if d.endswith('_swapped_frames')]
        
        if not swapped_folders:
            self.review_log("No swapped frame folders found in Temp.")
            return
            
        face_analyzer = insightface.app.FaceAnalysis(providers=[self.config['GPU_PROVIDER']])
        face_analyzer.prepare(ctx_id=0, det_size=(640, 640))
        
        for folder in swapped_folders:
            swapped_path = os.path.join(temp_dir, folder)
            unswapped_path = os.path.join(temp_dir, folder.replace('_swapped_frames', '_unswapped'))
            os.makedirs(unswapped_path, exist_ok=True)
            
            self.review_log(f"Scanning: {folder}")
            frames = sorted(os.listdir(swapped_path))
            missed_count = 0
            for frame_file in tqdm(frames, desc=f"Identifying in {folder}"):
                img = cv2.imread(os.path.join(swapped_path, frame_file))
                if img is None: continue
                
                faces = face_analyzer.get(img)
                if not faces:
                    shutil.copy(os.path.join(swapped_path, frame_file), os.path.join(unswapped_path, frame_file))
                    missed_count += 1
            self.review_log(f"Found {missed_count} potentially unswapped frames in {folder}.")
        self.review_log("--- Identification Complete ---")

    def reswap_unswapped(self):
        threading.Thread(target=self._reswap_unswapped_thread).start()

    def _reswap_unswapped_thread(self):
        self.review_log("--- Starting Re-Swap Process ---")
        temp_dir = self.config['TEMP_DIR']
        unswapped_folders = [d for d in os.listdir(temp_dir) if d.endswith('_unswapped')]

        if not unswapped_folders:
            self.review_log("No unswapped folders found to process.")
            return
            
        source_face_data = load_source_face_index(
            os.path.join(temp_dir, 'source_faces_index.pkl'))
            
        face_analyzer = insightface.app.FaceAnalysis(providers=[self.config['GPU_PROVIDER']])
        face_analyzer.prepare(ctx_id=0, det_size=(640, 640))
        face_swapper = load_face_swapper(self.config, [self.config['GPU_PROVIDER']])
        post_chain = load_post_process_chain(self.config, [self.config['GPU_PROVIDER']], self.review_log)

        for folder in unswapped_folders:
            unswapped_path = os.path.join(temp_dir, folder)
            original_frames_path = os.path.join(temp_dir, folder.replace('_unswapped', '_frames'))
            swapped_dest_path = os.path.join(temp_dir, folder.replace('_unswapped', '_swapped_frames'))
            
            self.review_log(f"Re-swapping frames for: {folder}")
            frames_to_fix = sorted(os.listdir(unswapped_path))
            for frame_file in tqdm(frames_to_fix, desc=f"Fixing in {folder}"):
                original_img = cv2.imread(os.path.join(original_frames_path, frame_file))
                if original_img is None: continue
                
                target_faces = face_analyzer.get(original_img)
                final_img = original_img.copy()
                if target_faces:
                    for target_face in target_faces:
                        distances = [1 - np.dot(target_face.normed_embedding, data['embedding']) for data in source_face_data]
                        best_match_index = np.argmin(distances)
                        source_face = indexed_source_face(source_face_data[best_match_index])
                        swapped_img = face_swapper.get(final_img, target_face, source_face, paste_back=True)
                        swapped_img = post_chain.protect_occlusions(final_img, swapped_img, target_face)
                        if self.config['ENABLE_COLOR_CORRECTION']:
                            final_img = correct_colors(final_img, swapped_img, target_face)
                        else:
                            final_img = swapped_img
                        final_img = post_chain.process_face(final_img, target_face)
                final_img = post_chain.finish_frame(final_img)
                cv2.imwrite(os.path.join(swapped_dest_path, frame_file), final_img)
            
            shutil.rmtree(unswapped_path) # Clean up after fixing
            self.review_log(f"Finished re-swapping for {folder}.")
        self.review_log("--- Re-Swap Complete ---")

# ==============================================================================
# --- 3. CORE PROCESSING WORKFLOWS ---
# ==============================================================================

def process_video(base_config, video_file, log, pause_event, stop_event, is_resume):
    video_config = base_config.copy()
    video_config['IS_VIDEO'] = True
    video_name_part = os.path.splitext(video_file)[0]
    source_folder_name = os.path.basename(os.path.normpath(video_config['SOURCE_IMAGES_DIR']))
    
    # Update temp paths to be video-specific
    video_config['FRAMES_DIR'] = os.path.join(base_config['TEMP_DIR'], f"{video_name_part}-{source_folder_name}_frames")
    video_config['SWAPPED_FRAMES_DIR'] = os.path.join(base_config['TEMP_DIR'], f"{video_name_part}-{source_folder_name}_swapped_frames")
    video_config['INDEX_FILE_PATH'] = os.path.join(base_config['TEMP_DIR'], 'source_faces_index.pkl') # Index is shared

    video_config['TARGET_VIDEO_PATH'] = os.path.join(base_config['TARGET_DIR'], video_file)
    video_config['FINAL_VIDEO_PATH'] = os.path.join(base_config['OUTPUT_DIR'], f"{video_name_part}-{source_folder_name}_swapped.mp4")

    if os.path.exists(video_config['FINAL_VIDEO_PATH']):
        if not video_config.get('REPROCESS_EXISTING', False):
            log(
                "Output file already exists. Skipping: "
                f"{video_config['FINAL_VIDEO_PATH']} (enable Reprocess existing outputs to run it again)"
            )
            return
        log(f"Reprocessing and replacing existing output: {video_config['FINAL_VIDEO_PATH']}")

    if not is_resume:
        step_1_extract_frames(video_config, log)
    else:
        log("--> STEP 1: Skipping frame extraction in resume mode.")
    
    if stop_event.is_set(): return
    step_3_swap_faces(video_config, log, pause_event, stop_event)
    if stop_event.is_set(): return
    
    if video_config.get('ENABLE_REVIEW_PASS', True):
        step_3b_review_and_fix_misses(video_config, log, pause_event, stop_event)
        if stop_event.is_set(): return

    if not video_config.get('ENABLE_MANUAL_REVIEW', False):
        step_4_create_final_video(video_config, log)
        cleanup_temp_folder(video_config, log)

def process_image(base_config, image_file, log):
    image_config = base_config.copy()
    image_config['IS_VIDEO'] = False
    image_config['TARGET_IMAGE_PATH'] = os.path.join(base_config['TARGET_DIR'], image_file)
    image_name_part = os.path.splitext(image_file)[0]
    source_folder_name = os.path.basename(os.path.normpath(image_config['SOURCE_IMAGES_DIR']))
    image_ext = os.path.splitext(image_file)[1]
    image_config['FINAL_IMAGE_PATH'] = os.path.join(base_config['OUTPUT_DIR'], f"{image_name_part}-{source_folder_name}_swapped{image_ext}")

    if os.path.exists(image_config['FINAL_IMAGE_PATH']):
        if not image_config.get('REPROCESS_EXISTING', False):
            log(
                "Output file already exists. Skipping: "
                f"{image_config['FINAL_IMAGE_PATH']} (enable Reprocess existing outputs to run it again)"
            )
            return
        log(f"Reprocessing and replacing existing output: {image_config['FINAL_IMAGE_PATH']}")
        
    swap_single_image(image_config, log)

# ==============================================================================
# --- 4. SETUP AND HELPER FUNCTIONS ---
# ==============================================================================

def setup_project_structure(config):
    for path_key in ['SOURCE_IMAGES_DIR', 'TARGET_DIR', 'OUTPUT_DIR', 'TEMP_DIR', 'MODELS_DIR']:
        os.makedirs(config[path_key], exist_ok=True)

def download_swapper_model(config, log):
    model_path = config['SWAPPER_MODEL_PATH']
    if os.path.exists(model_path): return
    model_filename = os.path.basename(model_path)
    log(f"Model {model_filename} not found. Downloading...")
    model_info = SWAPPER_MODELS.get(config.get('SWAPPER_MODEL_CHOICE'))
    if model_info is None:
        url = f"https://huggingface.co/deepinsight/inswapper/resolve/main/{model_filename}"
    else:
        url = model_info['url']
    partial_path = model_path + '.part'
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        with open(partial_path, 'wb') as f:
            for data in response.iter_content(chunk_size=1024 * 1024):
                if data:
                    f.write(data)
        if os.path.getsize(partial_path) < 1024 * 1024:
            raise RuntimeError('Downloaded model file is unexpectedly small.')
        os.replace(partial_path, model_path)
        log("    Model downloaded successfully.")
    except (requests.exceptions.RequestException, OSError, RuntimeError) as e:
        if os.path.exists(partial_path):
            os.remove(partial_path)
        raise Exception(f"Failed to download model: {e}. Please check your internet connection.")


def _download_model(model_path, url, display_name, log):
    if os.path.exists(model_path):
        return
    log(f"Model {display_name} not found. Downloading...")
    partial_path = model_path + '.part'
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        total = int(response.headers.get('content-length', 0))
        received = 0
        with open(partial_path, 'wb') as f:
            for data in response.iter_content(chunk_size=1024 * 1024):
                if data:
                    f.write(data)
                    received += len(data)
                    if total and received % (50 * 1024 * 1024) < len(data):
                        log(f"    {display_name}: {received / total * 100:.0f}%")
        if os.path.getsize(partial_path) < 1024 * 1024:
            raise RuntimeError('Downloaded model file is unexpectedly small.')
        os.replace(partial_path, model_path)
        log(f"    {display_name} downloaded successfully.")
    except (requests.exceptions.RequestException, OSError, RuntimeError) as e:
        if os.path.exists(partial_path):
            os.remove(partial_path)
        raise RuntimeError(f"Failed to download {display_name}: {e}") from e


def download_post_process_models(config, log):
    selected = []
    if config.get('FACE_RESTORER') in (
            'CodeFormer', 'GFPGAN 1024', 'RestoreFormer++', 'GPEN 512', 'GPEN 1024'):
        selected.append(config['FACE_RESTORER'])
    colorizer = config.get('COLORIZATION_MODEL', 'Off')
    if colorizer != 'Off':
        selected.append(colorizer)
    if config.get('UPSCALE_FACTOR') in ('2x', '4x'):
        upscale_names = {
            'RealESRGAN': 'RealESRGAN x4',
            'UltraSharp': 'UltraSharp 4x',
            'UltraMix Smooth': 'UltraMix Smooth 4x',
        }
        selected.append(upscale_names.get(config.get('UPSCALE_MODEL'), 'RealESRGAN x4'))
    if config.get('ENABLE_SMART_MASKING'):
        selected.extend(['Occluder', 'FaceParser', 'XSeg'])
    for name in selected:
        info = POST_PROCESS_MODELS[name]
        _download_model(os.path.join(config['MODELS_DIR'], info['filename']),
                        info['url'], name, log)


def load_face_swapper(config, providers):
    """Load and validate an InsightFace-compatible 128/256 swapper model."""
    model_path = config['SWAPPER_MODEL_PATH']
    try:
        expected_size = config.get('EXPECTED_SWAPPER_SIZE')
        if expected_size == 256:
            # InsightFace's ModelRouter recognizes INSwapper only when the
            # first input is 128x128. ReSwapper's compatible model uses the
            # same INSwapper interface with a 256x256 image input, so create
            # the runtime session and wrapper directly.
            from insightface.model_zoo.inswapper import INSwapper
            session = onnxruntime.InferenceSession(model_path, providers=providers)
            swapper = INSwapper(model_file=model_path, session=session)
        else:
            swapper = insightface.model_zoo.get_model(model_path, providers=providers)
        if swapper is None:
            raise RuntimeError('InsightFace did not recognize the ONNX graph.')
    except Exception as e:
        raise RuntimeError(
            f"Could not load swapper model '{model_path}'. The 256 model must be "
            f"the originalInswapperClassCompatible ONNX build. Details: {e}. "
            f"If the download was interrupted, delete '{model_path}' and restart "
            "the application so it can download a clean copy."
        ) from e

    actual_size = getattr(swapper, 'input_size', None)
    if actual_size is not None:
        actual_size = tuple(int(value) for value in actual_size)
        if expected_size and actual_size != (expected_size, expected_size):
            raise RuntimeError(
                f"Swapper model input is {actual_size[0]}x{actual_size[1]}, but "
                f"{expected_size}x{expected_size} was expected. Check that the correct "
                "ONNX file is in the models folder."
            )
    return swapper


def _runtime_providers(preferred):
    available = onnxruntime.get_available_providers()
    providers = [p for p in preferred if p in available]
    if 'CPUExecutionProvider' in available and 'CPUExecutionProvider' not in providers:
        providers.append('CPUExecutionProvider')
    return providers or ['CPUExecutionProvider']


class OnnxImageModel:
    """Small adapter for the Rope image-to-image ONNX exports."""
    def __init__(self, model_path, providers, mode, display_name=None):
        self.mode = mode
        self.display_name = display_name or os.path.basename(model_path)
        self.session = onnxruntime.InferenceSession(
            model_path, providers=_runtime_providers(providers))
        self.inputs = self.session.get_inputs()
        self.image_input = self.inputs[0]
        self.output_name = self.session.get_outputs()[0].name
        shape = self.image_input.shape
        self.height = int(shape[-2]) if isinstance(shape[-2], int) else None
        self.width = int(shape[-1]) if isinstance(shape[-1], int) else None
        self.dtype = self._numpy_dtype(self.image_input.type)

    @staticmethod
    def _numpy_dtype(onnx_type):
        """Map ONNX Runtime's tensor type string to the exact NumPy dtype."""
        onnx_type = onnx_type.lower()
        if 'float16' in onnx_type:
            return np.float16
        if 'double' in onnx_type or 'float64' in onnx_type:
            return np.float64
        if 'float' in onnx_type:
            return np.float32
        raise TypeError(f"Unsupported ONNX image input type: {onnx_type}")

    @staticmethod
    def _shape_for_aux(inp):
        return tuple(int(v) if isinstance(v, int) and v > 0 else 1 for v in inp.shape)

    def run(self, bgr_image, strength=0.7):
        h = self.height or bgr_image.shape[0]
        w = self.width or bgr_image.shape[1]
        resized = cv2.resize(bgr_image, (w, h), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        if self.mode == 'face':
            rgb = (rgb - 0.5) / 0.5
        blob = np.transpose(rgb, (2, 0, 1))[None].astype(self.dtype)
        feeds = {self.image_input.name: blob}
        for inp in self.inputs[1:]:
            dtype = self._numpy_dtype(inp.type)
            value = strength if any(k in inp.name.lower() for k in ('w', 'weight', 'fidelity')) else 0.0
            feeds[inp.name] = np.full(self._shape_for_aux(inp), value, dtype=dtype)
        output = self.session.run([self.output_name], feeds)[0]
        if not np.all(np.isfinite(output)):
            raise RuntimeError(f"{self.display_name} returned NaN or infinite pixels")
        if output.ndim == 4:
            output = output[0]
        if output.ndim == 3 and output.shape[0] in (1, 3, 4):
            output = np.transpose(output, (1, 2, 0))
        output = output.astype(np.float32)
        if output.min() < -0.05:
            output = (output + 1.0) / 2.0
        elif output.max() > 2.0:
            output = output / 255.0
        output = np.clip(output, 0.0, 1.0)
        if output.ndim == 2:
            output = cv2.cvtColor(output, cv2.COLOR_GRAY2RGB)
        if output.shape[2] > 3:
            output = output[:, :, :3]
        result = cv2.cvtColor((output * 255.0).round().astype(np.uint8), cv2.COLOR_RGB2BGR)
        # Never paste a failed inference crop over the image. Some model/provider
        # combinations return an all-black tensor instead of raising an error.
        if result.max() < 8 or (result.mean() < 2.0 and resized.mean() > 8.0):
            raise RuntimeError(f"{self.display_name} returned an invalid black image")
        return result


class DDColorModel:
    """DDColor adapter: predicts Lab a/b channels for a complete image."""
    def __init__(self, model_path, providers, display_name):
        self.display_name = display_name
        self.session = onnxruntime.InferenceSession(
            model_path, providers=_runtime_providers(providers))
        self.input = self.session.get_inputs()[0]
        self.output_name = self.session.get_outputs()[0].name
        self.dtype = OnnxImageModel._numpy_dtype(self.input.type)
        shape = self.input.shape
        self.height = int(shape[-2]) if isinstance(shape[-2], int) else 512
        self.width = int(shape[-1]) if isinstance(shape[-1], int) else 512

    def run(self, bgr_image):
        rgb = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        original_lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
        original_l = original_lab[:, :, 0]
        small = cv2.resize(rgb, (self.width, self.height), interpolation=cv2.INTER_AREA)
        small_l = cv2.cvtColor(small, cv2.COLOR_RGB2LAB)[:, :, 0]
        gray_lab = np.zeros_like(small, dtype=np.float32)
        gray_lab[:, :, 0] = small_l
        gray_rgb = cv2.cvtColor(gray_lab, cv2.COLOR_LAB2RGB)
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        blob = ((gray_rgb - mean) / std).transpose(2, 0, 1)[None].astype(self.dtype)
        output = self.session.run([self.output_name], {self.input.name: blob})[0]
        if not np.all(np.isfinite(output)):
            raise RuntimeError(f'{self.display_name} returned invalid pixels')
        if output.ndim == 4:
            output = output[0]
        if output.shape[0] == 2:
            output = output.transpose(1, 2, 0)
        ab = cv2.resize(output.astype(np.float32),
                        (bgr_image.shape[1], bgr_image.shape[0]),
                        interpolation=cv2.INTER_CUBIC)
        lab = np.concatenate((original_l[:, :, None], ab), axis=2).astype(np.float32)
        colored_rgb = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
        colored_rgb = np.clip(colored_rgb, 0.0, 1.0)
        return cv2.cvtColor((colored_rgb * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)


class SmartMaskModels:
    """Combines occlusion, face parsing and XSeg masks for safer blending."""
    def __init__(self, models_dir, providers):
        runtime = _runtime_providers(providers)
        self.sessions = {}
        for name in ('Occluder', 'FaceParser', 'XSeg'):
            info = POST_PROCESS_MODELS[name]
            self.sessions[name] = onnxruntime.InferenceSession(
                os.path.join(models_dir, info['filename']), providers=runtime)

    @staticmethod
    def _infer(session, image, parser=False):
        inp = session.get_inputs()[0]
        shape = inp.shape
        nchw = len(shape) == 4 and (shape[1] in (1, 3) or not isinstance(shape[-1], int))
        height = int(shape[2] if nchw and isinstance(shape[2], int) else
                     shape[1] if not nchw and isinstance(shape[1], int) else 512 if parser else 256)
        width = int(shape[3] if nchw and isinstance(shape[3], int) else
                    shape[2] if not nchw and isinstance(shape[2], int) else 512 if parser else 256)
        rgb = cv2.cvtColor(cv2.resize(image, (width, height)), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        if parser:
            rgb = ((rgb - np.array([0.485, 0.456, 0.406], np.float32)) /
                   np.array([0.229, 0.224, 0.225], np.float32))
        blob = rgb.transpose(2, 0, 1)[None] if nchw else rgb[None]
        dtype = OnnxImageModel._numpy_dtype(inp.type)
        return session.run(None, {inp.name: blob.astype(dtype)})[0]

    def protection_mask(self, aligned_face):
        occ = np.squeeze(self._infer(self.sessions['Occluder'], aligned_face))
        xseg = np.squeeze(self._infer(self.sessions['XSeg'], aligned_face))
        parser = self._infer(self.sessions['FaceParser'], aligned_face, parser=True)

        def normalize(mask):
            mask = mask.astype(np.float32)
            if mask.ndim == 3:
                mask = mask[0] if mask.shape[0] == 1 else mask.mean(axis=0)
            if mask.min() < 0 or mask.max() > 1:
                mask = 1.0 / (1.0 + np.exp(-np.clip(mask, -30, 30)))
            return np.clip(mask, 0, 1)

        occ = normalize(occ)
        xseg = normalize(xseg)
        if parser.ndim == 4:
            parser = parser[0]
        if parser.ndim == 3 and parser.shape[0] > 3:
            labels = np.argmax(parser, axis=0)
        elif parser.ndim == 3 and parser.shape[-1] > 3:
            labels = np.argmax(parser, axis=-1)
        else:
            labels = np.zeros(parser.shape[-2:], dtype=np.int32)
        # CelebAMask-HQ labels: eyeglasses=3, hair=13, hat=14.
        parsed_protection = np.isin(labels, [3, 13, 14]).astype(np.float32)
        size = (aligned_face.shape[1], aligned_face.shape[0])
        occ = cv2.resize(occ, size, interpolation=cv2.INTER_LINEAR)
        xseg = cv2.resize(xseg, size, interpolation=cv2.INTER_LINEAR)
        parsed_protection = cv2.resize(parsed_protection, size, interpolation=cv2.INTER_NEAREST)
        protection = np.maximum(occ * (1.0 - xseg), parsed_protection)
        return cv2.GaussianBlur(np.clip(protection, 0, 1), (15, 15), 0)


class LocalPromptEditor:
    MODEL_ID = 'timbrooks/instruct-pix2pix'

    def __init__(self, log):
        self.log = log
        try:
            import torch
            from diffusers import StableDiffusionInstructPix2PixPipeline
            from diffusers import EulerAncestralDiscreteScheduler
        except ImportError as e:
            raise RuntimeError(
                "Local prompt editing requires PyTorch and Diffusers. Install them with: "
                "python -m pip install -U diffusers transformers accelerate safetensors pillow"
            ) from e
        if not torch.cuda.is_available():
            raise RuntimeError(
                "Local prompt editing is enabled, but CUDA is unavailable. Install a "
                "CUDA-enabled PyTorch build and confirm that the NVIDIA driver is working."
            )
        self.torch = torch
        log(f"    Loading local prompt model: {self.MODEL_ID}")
        try:
            self.pipe = StableDiffusionInstructPix2PixPipeline.from_pretrained(
                self.MODEL_ID,
                torch_dtype=torch.float16,
                use_safetensors=True,
            )
        except Exception as e:
            raise RuntimeError(
                f"Could not download or load {self.MODEL_ID}: {e}"
            ) from e
        self.pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(
            self.pipe.scheduler.config)
        self.pipe.enable_attention_slicing()
        if hasattr(self.pipe, 'enable_vae_slicing'):
            self.pipe.enable_vae_slicing()
        self.pipe.to('cuda')
        memory_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        log(f"    Prompt editor ready on {torch.cuda.get_device_name(0)} ({memory_gb:.1f} GB VRAM).")

    def edit(self, bgr_image, prompt, negative_prompt='', steps=20):
        from PIL import Image
        original_h, original_w = bgr_image.shape[:2]
        scale = min(1.0, 768.0 / max(original_w, original_h))
        work_w = max(64, int(original_w * scale) // 8 * 8)
        work_h = max(64, int(original_h * scale) // 8 * 8)
        rgb = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        rgb = cv2.resize(rgb, (work_w, work_h), interpolation=cv2.INTER_AREA)
        pil_image = Image.fromarray(rgb)
        generator = self.torch.Generator(device='cuda').manual_seed(0)
        with self.torch.inference_mode():
            output = self.pipe(
                prompt=prompt,
                negative_prompt=negative_prompt or None,
                image=pil_image,
                num_inference_steps=int(steps),
                guidance_scale=7.5,
                image_guidance_scale=1.5,
                generator=generator,
            ).images[0]
        result = cv2.cvtColor(np.asarray(output), cv2.COLOR_RGB2BGR)
        if result.shape[:2] != (original_h, original_w):
            result = cv2.resize(result, (original_w, original_h), interpolation=cv2.INTER_LANCZOS4)
        return result


class CloudImageEditor:
    """High-fidelity reference image editing through the OpenAI Images API."""
    def __init__(self, model, quality, log):
        api_key = os.environ.get('OPENAI_API_KEY', '').strip()
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Configure the key before enabling Cloud prompt editing."
            )
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError(
                "Cloud prompt editing requires the OpenAI package. Install it with: "
                "python -m pip install -U openai"
            ) from e
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.quality = quality
        self.log = log
        log(f"    Cloud prompt editor ready: {model}, quality={quality}")

    @staticmethod
    def _supported_size(width, height):
        """Choose a supported custom size while preserving aspect ratio."""
        if width <= 0 or height <= 0:
            return 'auto'
        ratio = width / height
        if ratio < (1.0 / 3.0) or ratio > 3.0:
            return 'auto'
        pixels = width * height
        min_pixels = 655360
        max_pixels = 8294400
        scale = 1.0
        if pixels < min_pixels:
            scale = (min_pixels / pixels) ** 0.5
        if pixels * scale * scale > max_pixels:
            scale = (max_pixels / pixels) ** 0.5
        if max(width, height) * scale > 3840:
            scale = min(scale, 3840.0 / max(width, height))
        out_w = max(16, int(round(width * scale / 16.0)) * 16)
        out_h = max(16, int(round(height * scale / 16.0)) * 16)
        return f'{out_w}x{out_h}'

    @staticmethod
    def _api_error_details(error):
        """Extract the useful API message from recent and older SDK errors."""
        parts = []
        body = getattr(error, 'body', None)
        if body:
            parts.append(str(body))
        response = getattr(error, 'response', None)
        if response is not None:
            try:
                response_text = response.text
                if response_text:
                    parts.append(str(response_text))
            except Exception:
                pass
        for attribute in ('message', 'code', 'param', 'type'):
            value = getattr(error, attribute, None)
            if value:
                parts.append(f'{attribute}={value}')
        parts.append(str(error))
        unique = []
        for part in parts:
            part = ' '.join(str(part).split())
            if part and part not in unique:
                unique.append(part)
        return ' | '.join(unique)

    def edit(self, bgr_image, prompt, negative_prompt='', steps=20):
        del steps  # Local diffusion-only setting.
        original_h, original_w = bgr_image.shape[:2]
        success, encoded = cv2.imencode('.png', bgr_image)
        if not success:
            raise RuntimeError('Could not encode the image for cloud editing.')
        image_file = BytesIO(encoded.tobytes())
        image_file.name = 'input.png'
        preservation = (
            "Edit only what the user requests. Preserve the person's exact identity, face, "
            "expression, eyes, skin, body, pose, clothing, lighting, background, composition, "
            "and camera angle unless the request explicitly changes one of them. "
        )
        full_prompt = preservation + prompt.strip()
        if negative_prompt.strip():
            full_prompt += " Do not add or introduce: " + negative_prompt.strip() + "."
        try:
            response = self.client.images.edit(
                model=self.model,
                image=image_file,
                prompt=full_prompt,
                quality=self.quality,
                size='auto',
                output_format='png',
            )
        except Exception as first_error:
            # Retry the smallest valid edit request to work around SDK/API
            # parameter-version mismatches and reveal the real server error.
            self.log(
                '    Full cloud request was rejected; retrying with basic settings.'
            )
            image_file.seek(0)
            try:
                response = self.client.images.edit(
                    model=self.model,
                    image=image_file,
                    prompt=full_prompt,
                )
            except Exception as retry_error:
                raise RuntimeError(
                    'Cloud edit failed. Full request: '
                    f'{self._api_error_details(first_error)}; Basic retry: '
                    f'{self._api_error_details(retry_error)}'
                ) from retry_error
        if not response.data or not response.data[0].b64_json:
            raise RuntimeError('The cloud editor returned no image.')
        result_bytes = base64.b64decode(response.data[0].b64_json)
        result = cv2.imdecode(np.frombuffer(result_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if result is None:
            raise RuntimeError('The cloud editor returned an unreadable image.')
        if result.shape[:2] != (original_h, original_w):
            result = cv2.resize(result, (original_w, original_h), interpolation=cv2.INTER_LANCZOS4)
        return result


class QwenCloudImageEditor:
    """Qwen-Image-Edit through Hugging Face Inference Providers."""
    def __init__(self, model, log):
        token = os.environ.get('HF_TOKEN', '').strip()
        if not token:
            raise RuntimeError(
                'HF_TOKEN is not set. Run Configure_HuggingFace_Token.bat '
                'before enabling Qwen Cloud.'
            )
        try:
            from huggingface_hub import InferenceClient
        except ImportError as e:
            raise RuntimeError(
                'Qwen Cloud requires huggingface_hub. Install it with: '
                'python -m pip install -U huggingface_hub'
            ) from e
        self.client = InferenceClient(provider='fal-ai', api_key=token, timeout=600)
        self.model = model
        self.log = log
        log(f'    Qwen Cloud editor ready: {model} through fal-ai')

    def edit(self, bgr_image, prompt, negative_prompt='', steps=20):
        from PIL import Image
        original_h, original_w = bgr_image.shape[:2]
        success, encoded = cv2.imencode('.png', bgr_image)
        if not success:
            raise RuntimeError('Could not encode the image for Qwen Cloud editing.')
        image_bytes = encoded.tobytes()

        def run_edit(edit_prompt, edit_negative=None, guidance=4.5):
            edited = self.client.image_to_image(
                image_bytes,
                prompt=edit_prompt,
                negative_prompt=edit_negative or None,
                num_inference_steps=max(28, min(50, int(steps))),
                guidance_scale=guidance,
                model=self.model,
            )
            if isinstance(edited, bytes):
                edited = Image.open(BytesIO(edited))
            rgb = np.asarray(edited.convert('RGB'))
            candidate = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            if candidate.shape[:2] != (original_h, original_w):
                candidate = cv2.resize(
                    candidate, (original_w, original_h), interpolation=cv2.INTER_LANCZOS4
                )
            return candidate

        try:
            result = run_edit(
                prompt.strip(), negative_prompt.strip() or None, guidance=4.5
            )
            first_change = float(np.mean(cv2.absdiff(result, bgr_image)))
            self.log(f'    Qwen first-attempt pixel-change score: {first_change:.2f}')
            if first_change < 1.0:
                self.log('    Qwen returned almost no edit; automatically retrying with a stronger instruction.')
                retry_prompt = (
                    'Make a clearly visible image edit. ' + prompt.strip() +
                    ' The requested change must be obvious in the output. '
                    'Preserve the person, face, pose, framing, lighting, and background.'
                )
                retry_result = run_edit(retry_prompt, None, guidance=4.5)
                retry_change = float(np.mean(cv2.absdiff(retry_result, bgr_image)))
                self.log(f'    Qwen retry pixel-change score: {retry_change:.2f}')
                if retry_change > first_change:
                    result = retry_result
        except Exception as e:
            raise RuntimeError(f'Qwen Cloud edit failed: {e}') from e
        return result


class A2EImageEditor:
    """Prompt-guided Qwen image editing through the official A2E REST API."""
    API_ROOT = 'https://api.a2e.ai'

    def __init__(self, model, resolution, log):
        self.token = (os.environ.get('A2E_API_TOKEN') or
                      os.environ.get('A2E_TOKEN') or '').strip()
        if not self.token:
            raise RuntimeError(
                'A2E_API_TOKEN is not set. Run Configure_A2E_API_Token.bat '
                'before selecting the A2E prompt engine.'
            )
        self.model = model
        self.resolution = resolution
        self.log = log
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
        }
        log(f'    A2E editor ready: {model} at {resolution}')

    @staticmethod
    def _response_json(response, action):
        try:
            payload = response.json()
        except Exception:
            payload = {'message': response.text[:500]}
        if not response.ok:
            message = payload.get('message') or payload.get('msg') or payload
            raise RuntimeError(f'A2E {action} failed ({response.status_code}): {message}')
        if isinstance(payload, dict) and payload.get('code') not in (None, 0, 200):
            message = payload.get('message') or payload.get('msg') or payload
            raise RuntimeError(f'A2E {action} failed: {message}')
        return payload

    @staticmethod
    def _find_value(value, keys):
        if isinstance(value, dict):
            for key in keys:
                if key in value and value[key] not in (None, ''):
                    return value[key]
            for child in value.values():
                found = A2EImageEditor._find_value(child, keys)
                if found not in (None, ''):
                    return found
        elif isinstance(value, list):
            for child in value:
                found = A2EImageEditor._find_value(child, keys)
                if found not in (None, ''):
                    return found
        return None

    @staticmethod
    def _output_url(payload, input_url):
        candidates = []
        input_marker = input_url.split('?', 1)[0].rstrip('/').rsplit('/', 1)[-1]

        def context_score(path):
            context = '.'.join(path).lower()
            if any(word in context for word in
                   ('input', 'source', 'reference', 'original', 'upload', 'cover')):
                return -100
            if any(word in context for word in
                   ('result', 'output', 'generated', 'final', 'completed')):
                return 100
            if any(word in context for word in ('image_urls', 'images', 'media')):
                return 20
            return 0

        def walk(value, path=()):
            if isinstance(value, dict):
                for key, child in value.items():
                    walk(child, path + (str(key),))
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    walk(child, path + (str(index),))
            elif isinstance(value, str) and value.startswith(('http://', 'https://')):
                score = context_score(path)
                lower_path = value.lower().split('?', 1)[0]
                looks_like_image = any(lower_path.endswith(ext) for ext in
                                       ('.png', '.jpg', '.jpeg', '.webp'))
                if score >= 0 and (looks_like_image or score >= 20):
                    candidates.append((score, value, '.'.join(path)))

        walk(payload)
        candidates.sort(key=lambda item: item[0], reverse=True)
        for score, url, field_path in candidates:
            if url == input_url or (input_marker and input_marker in url):
                continue
            return url
        return None

    def _upload_png(self, image_bytes):
        object_key = f'ai-generator/{int(time.time() * 1000)}-{hashlib.sha256(image_bytes).hexdigest()[:12]}.png'
        response = requests.post(
            f'{self.API_ROOT}/v1/r2/upload-presigned-url',
            headers=self.headers,
            json={
                'key': object_key,
                'purpose': 'STAGING',
                'expiresIn': 300,
                'contentType': 'image/png',
                'fileSize': len(image_bytes),
            },
            timeout=60,
        )
        payload = self._response_json(response, 'upload preparation')
        data = payload.get('data') or {}
        upload_url, cdn_url = data.get('uploadUrl'), data.get('cdnUrl')
        if not upload_url or not cdn_url:
            raise RuntimeError('A2E upload preparation returned no uploadUrl/cdnUrl.')
        uploaded = requests.put(
            upload_url,
            data=image_bytes,
            headers={'Content-Type': 'image/png', 'Content-Length': str(len(image_bytes))},
            timeout=180,
        )
        if not uploaded.ok:
            raise RuntimeError(f'A2E image upload failed ({uploaded.status_code}).')
        return cdn_url

    def _size_for_image(self, width, height):
        is_2k = self.resolution == '2K' and self.model == 'qwen-image-3.0-pro'
        if is_2k:
            if abs(width - height) / max(width, height) < 0.12:
                return '2048*2048'
            return '2048*1365' if width > height else '1365*2048'
        if abs(width - height) / max(width, height) < 0.12:
            return '1024*1024'
        return '1328*880' if width > height else '880*1328'

    def edit(self, bgr_image, prompt, negative_prompt='', steps=20):
        original_h, original_w = bgr_image.shape[:2]
        success, encoded = cv2.imencode('.png', bgr_image)
        if not success:
            raise RuntimeError('Could not encode the image for A2E editing.')
        input_url = self._upload_png(encoded.tobytes())
        full_prompt = prompt.strip()
        is_gpt = self.model.startswith('gpt-image-')
        is_nano = self.model.startswith('nano-banana')
        # A2E's GPT/Nano endpoints have no negative_prompt field. Folding a
        # long negative list into the instruction can over-constrain the edit
        # and cause a near-identical result, so only Qwen receives it.
        if negative_prompt.strip() and not (is_gpt or is_nano):
            full_prompt += ' Avoid: ' + negative_prompt.strip() + '.'
        body = {
            'name': 'AI Generator prompt edit',
            'prompt': full_prompt,
            'creation_mode': 'image-edit',
            'model': self.model,
            'input_images': [input_url],
            'minor_suspected_skip': False,
        }
        if is_nano:
            body.update({
                'aspect_ratio': 'auto',
                'image_size': '1K' if self.model == 'nano-banana-2-lite' else self.resolution,
                'google_search': False,
            })
            start_path = '/v1/userNanoBanana/start'
            detail_path = '/v1/userNanoBanana/detail/{id}'
        elif is_gpt:
            body.update({
                'aspect_ratio': 'auto',
                'resolution': self.resolution,
                'save_as_png': True,
                'background': 'opaque',
                'force_generate': False,
            })
            start_path = '/v1/userGptImage/start'
            detail_path = '/v1/userGptImage/detail/{id}'
        else:
            body['size'] = self._size_for_image(original_w, original_h)
            start_path = '/v1/userQwen2Image/start'
            detail_path = '/v1/userQwen2Image/detail/{id}'
        response = requests.post(
            f'{self.API_ROOT}{start_path}',
            headers=self.headers, json=body, timeout=90,
        )
        payload = self._response_json(response, 'task submission')
        task_id = self._find_value(payload, ('_id', 'task_id', 'taskId', 'id'))
        if not task_id:
            raise RuntimeError(f'A2E accepted the request but returned no task ID: {payload}')
        self.log(f'    A2E edit submitted; waiting for task {task_id}.')

        deadline = time.time() + 900
        last_status = ''
        while time.time() < deadline:
            time.sleep(3)
            detail_response = requests.get(
                f'{self.API_ROOT}{detail_path.format(id=task_id)}',
                headers=self.headers, timeout=60,
            )
            detail = self._response_json(detail_response, 'task status')
            status_value = self._find_value(
                detail, ('status', 'task_status', 'taskStatus', 'state')
            )
            status = str(status_value or '').lower()
            if status and status != last_status:
                self.log(f'    A2E task status: {status}')
                last_status = status
            if status in ('failed', 'error', 'cancelled', 'canceled', 'rejected'):
                message = self._find_value(detail, ('error', 'message', 'msg', 'fail_reason'))
                raise RuntimeError(f'A2E image edit failed: {message or detail}')
            result_url = self._output_url(detail, input_url)
            if result_url and (status in ('', 'success', 'succeeded', 'completed', 'done', 'finished')
                               or status_value is None):
                result_response = requests.get(result_url, timeout=180)
                result_response.raise_for_status()
                result = cv2.imdecode(
                    np.frombuffer(result_response.content, dtype=np.uint8), cv2.IMREAD_COLOR
                )
                if result is None:
                    raise RuntimeError('A2E returned an unreadable output image.')
                # Keep A2E's generated resolution (including 2K) so the later
                # face-swap/restoration stages do not discard cloud detail.
                return result
        raise RuntimeError('A2E image edit timed out after 15 minutes.')


_PROMPT_EDITOR_CACHE = None
_CLOUD_EDITOR_CACHE = {}
_QWEN_EDITOR_CACHE = {}
_A2E_EDITOR_CACHE = {}


def get_prompt_editor(log):
    global _PROMPT_EDITOR_CACHE
    if _PROMPT_EDITOR_CACHE is None:
        _PROMPT_EDITOR_CACHE = LocalPromptEditor(log)
    return _PROMPT_EDITOR_CACHE


def get_cloud_editor(model, quality, log):
    key = (model, quality)
    if key not in _CLOUD_EDITOR_CACHE:
        _CLOUD_EDITOR_CACHE[key] = CloudImageEditor(model, quality, log)
    return _CLOUD_EDITOR_CACHE[key]


def get_qwen_cloud_editor(model, log):
    if model not in _QWEN_EDITOR_CACHE:
        _QWEN_EDITOR_CACHE[model] = QwenCloudImageEditor(model, log)
    return _QWEN_EDITOR_CACHE[model]


def get_a2e_editor(model, resolution, log):
    key = (model, resolution)
    if key not in _A2E_EDITOR_CACHE:
        _A2E_EDITOR_CACHE[key] = A2EImageEditor(model, resolution, log)
    return _A2E_EDITOR_CACHE[key]


class PostProcessChain:
    def __init__(self, config, providers, log):
        self.config = config
        self.log = log
        self.restorer = None
        self.colorizer = None
        self.upscaler = None
        self.ddcolor = None
        self.masker = None
        self.prompt_editor = None
        models_dir = config['MODELS_DIR']
        restorer_name = config.get('FACE_RESTORER', 'None')
        if restorer_name in ('CodeFormer', 'GFPGAN 1024', 'RestoreFormer++',
                             'GPEN 512', 'GPEN 1024'):
            info = POST_PROCESS_MODELS[restorer_name]
            self.restorer = OnnxImageModel(os.path.join(models_dir, info['filename']), providers,
                                           'face', restorer_name)
            log(f"    Face restoration enabled: {restorer_name}")
        colorizer_name = config.get('COLORIZATION_MODEL', 'Off')
        if colorizer_name == 'ColorizeStable':
            info = POST_PROCESS_MODELS['ColorizeStable']
            self.colorizer = OnnxImageModel(os.path.join(models_dir, info['filename']), providers,
                                            'face', 'ColorizeStable')
            log("    ColorizeStable enabled.")
        elif colorizer_name in ('DDColor Natural', 'DDColor Artistic'):
            info = POST_PROCESS_MODELS[colorizer_name]
            self.ddcolor = DDColorModel(os.path.join(models_dir, info['filename']),
                                        providers, colorizer_name)
            log(f"    Colorization enabled: {colorizer_name}")
        if config.get('UPSCALE_FACTOR') in ('2x', '4x'):
            upscale_names = {
                'RealESRGAN': 'RealESRGAN x4',
                'UltraSharp': 'UltraSharp 4x',
                'UltraMix Smooth': 'UltraMix Smooth 4x',
            }
            upscale_name = upscale_names.get(config.get('UPSCALE_MODEL'), 'RealESRGAN x4')
            info = POST_PROCESS_MODELS[upscale_name]
            self.upscaler = OnnxImageModel(os.path.join(models_dir, info['filename']), providers,
                                           'upscale', upscale_name)
            log(f"    Upscaling enabled: {upscale_name} at {config['UPSCALE_FACTOR']}")
        if config.get('ENABLE_SMART_MASKING'):
            self.masker = SmartMaskModels(models_dir, providers)
            log("    Smart masking enabled: Occluder + FaceParser + XSeg")
        if config.get('ENABLE_PROMPT_EDIT'):
            if not config.get('EDIT_PROMPT'):
                log("    Prompt editing is enabled, but the edit prompt is empty; skipping it.")
            elif config.get('IS_VIDEO', True) and not config.get('PROMPT_FOR_VIDEOS'):
                log("    Prompt editing is disabled for video frames.")
            else:
                try:
                    prompt_engine = config.get('PROMPT_ENGINE', 'Local')
                    if prompt_engine == 'Cloud':
                        self.prompt_editor = get_cloud_editor(
                            config.get('CLOUD_IMAGE_MODEL', 'gpt-image-2.5-sunburst'),
                            config.get('CLOUD_IMAGE_QUALITY', 'high'),
                            log,
                        )
                    elif prompt_engine == 'Qwen Cloud':
                        self.prompt_editor = get_qwen_cloud_editor(
                            config.get('QWEN_IMAGE_MODEL', 'Qwen/Qwen-Image-Edit'),
                            log,
                        )
                    elif prompt_engine == 'A2E':
                        self.prompt_editor = get_a2e_editor(
                            config.get('A2E_IMAGE_MODEL', 'nano-banana-pro'),
                            config.get('A2E_RESOLUTION', '2K'),
                            log,
                        )
                    else:
                        self.prompt_editor = get_prompt_editor(log)
                except Exception as e:
                    # Prompt editing is optional. Missing CUDA/PyTorch should
                    # not prevent face swapping, restoration or upscaling.
                    self.prompt_editor = None
                    log(f"    Warning: Prompt editing was disabled: {e}")
        brightness = float(config.get('BRIGHTNESS', 0.0))
        gamma = float(config.get('GAMMA', 1.0))
        if abs(brightness) > 0.01 or abs(gamma - 1.0) > 0.001:
            log(f"    Tone correction enabled: brightness {brightness:+.0f}, gamma {gamma:.2f}")

    @staticmethod
    def _paste_aligned(image, processed_face, matrix):
        height, width = image.shape[:2]
        inverse = cv2.invertAffineTransform(matrix)
        restored = cv2.warpAffine(processed_face, inverse, (width, height),
                                  flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        mask = np.full(processed_face.shape[:2], 255, dtype=np.uint8)
        mask = cv2.warpAffine(mask, inverse, (width, height), flags=cv2.INTER_LINEAR)
        mask = cv2.erode(mask, np.ones((9, 9), np.uint8), iterations=1)
        mask = cv2.GaussianBlur(mask, (31, 31), 0).astype(np.float32) / 255.0
        return (restored * mask[:, :, None] + image * (1.0 - mask[:, :, None])).astype(np.uint8)

    def process_face(self, image, target_face):
        result = image
        for model in (self.restorer, self.colorizer):
            if model is None:
                continue
            crop_size = model.width or 512
            aligned, matrix = face_align.norm_crop2(result, target_face.kps, crop_size)
            try:
                processed = model.run(aligned, self.config.get('RESTORATION_STRENGTH', 0.7))
            except Exception as e:
                self.log(f"    Warning: skipped {model.display_name} for this face: {e}")
                continue
            if processed.shape[:2] != aligned.shape[:2]:
                processed = cv2.resize(processed, (aligned.shape[1], aligned.shape[0]), interpolation=cv2.INTER_CUBIC)
            result = self._paste_aligned(result, processed, matrix)
        return result

    def protect_occlusions(self, original, swapped, target_face):
        if self.masker is None:
            return swapped
        try:
            aligned_original, matrix = face_align.norm_crop2(original, target_face.kps, 512)
            aligned_swapped = cv2.warpAffine(swapped, matrix, (512, 512),
                                             flags=cv2.INTER_LINEAR,
                                             borderMode=cv2.BORDER_REFLECT)
            protection = self.masker.protection_mask(aligned_original)
            protected = (aligned_original * protection[:, :, None] +
                         aligned_swapped * (1.0 - protection[:, :, None])).astype(np.uint8)
            return self._paste_aligned(swapped, protected, matrix)
        except Exception as e:
            self.log(f"    Warning: skipped smart masking for this face: {e}")
            return swapped

    def apply_prompt(self, image):
        """Apply the selected prompt editor without other enhancement stages."""
        result = image
        if self.prompt_editor is not None:
            try:
                result = self.prompt_editor.edit(
                    result,
                    self.config.get('EDIT_PROMPT', ''),
                    self.config.get('NEGATIVE_PROMPT', ''),
                    self.config.get('PROMPT_STEPS', 20),
                )
                engine = self.config.get('PROMPT_ENGINE', 'Local')
                self.log(f"    {engine} prompt edit completed for this image/frame.")
            except Exception as e:
                details = getattr(e, 'body', None)
                if isinstance(details, dict):
                    error_info = details.get('error', details)
                    if isinstance(error_info, dict):
                        details = error_info.get('message') or error_info
                detail_text = str(details).strip() if details else str(e).strip()
                self.log(
                    "    Warning: skipped prompt editing for this image/frame: "
                    f"{detail_text}"
                )
        return result

    def finish_frame(self, image, include_prompt=True):
        result = image
        if self.ddcolor is not None:
            try:
                result = self.ddcolor.run(result)
            except Exception as e:
                self.log(f"    Warning: skipped {self.ddcolor.display_name}: {e}")
        if include_prompt:
            result = self.apply_prompt(result)
        brightness = float(self.config.get('BRIGHTNESS', 0.0))
        gamma = max(0.2, min(3.0, float(self.config.get('GAMMA', 1.0))))
        if abs(brightness) > 0.01:
            result = np.clip(result.astype(np.float32) + brightness, 0, 255).astype(np.uint8)
        if abs(gamma - 1.0) > 0.001:
            gamma_lut = np.array([
                ((value / 255.0) ** (1.0 / gamma)) * 255.0
                for value in range(256)
            ], dtype=np.uint8)
            result = cv2.LUT(result, gamma_lut)
        if self.upscaler is None:
            return result
        try:
            result = self.upscaler.run(result)
        except Exception as e:
            self.log(f"    Warning: skipped {self.upscaler.display_name} for this frame: {e}")
            return result
        if self.config.get('UPSCALE_FACTOR') == '2x':
            target = (image.shape[1] * 2, image.shape[0] * 2)
            result = cv2.resize(result, target, interpolation=cv2.INTER_LANCZOS4)
        return result


def load_post_process_chain(config, providers, log):
    try:
        return PostProcessChain(config, providers, log)
    except Exception as e:
        if providers != ['CPUExecutionProvider']:
            log(f"    Post-processing GPU load failed; trying CPU. Error: {e}")
            return PostProcessChain(config, ['CPUExecutionProvider'], log)
        raise RuntimeError(f"Could not load post-processing model: {e}") from e

def correct_colors(original_img, swapped_img, target_face):
    h, w, _ = original_img.shape
    face_landmarks = target_face.landmark_2d_106
    mask = np.zeros((h, w), dtype=np.uint8)
    points = np.array([[int(p[0]), int(p[1])] for p in face_landmarks])
    convexhull = cv2.convexHull(points)
    cv2.fillConvexPoly(mask, convexhull, 255)
    mask = cv2.GaussianBlur(mask, (21, 21), 0)
    r = cv2.boundingRect(mask)
    center = (r[0] + int(r[2] / 2), r[1] + int(r[3] / 2))
    return cv2.seamlessClone(swapped_img, original_img, mask, center, cv2.NORMAL_CLONE)

def cleanup_temp_folder(config, log, is_manual=False):
    path_to_clean = config['TEMP_DIR'] if is_manual else config.get('FRAMES_DIR')
    if is_manual:
        log("--> Cleaning up entire temporary directory...")
    else:
        log("--> Cleaning up temporary files for video...")

    if os.path.exists(path_to_clean):
        shutil.rmtree(path_to_clean)
    
    if is_manual:
        os.makedirs(path_to_clean, exist_ok=True)
    else:
        # Also clean swapped frames for the specific video
        if os.path.exists(config['SWAPPED_FRAMES_DIR']):
            shutil.rmtree(config['SWAPPED_FRAMES_DIR'])

    log("    Folder cleaned.")


def select_largest_face(faces):
    """Return the main face and ignore small low-confidence background detections."""
    if not faces:
        return None
    return max(faces, key=lambda face: max(0, face.bbox[2] - face.bbox[0]) *
                                      max(0, face.bbox[3] - face.bbox[1]))


def indexed_source_face(source_data):
    """INSWapper only needs the normalized source embedding for identity."""
    return SimpleNamespace(normed_embedding=source_data['embedding'])


def load_source_face_index(index_path):
    with open(index_path, 'rb') as f:
        source_face_data = pickle.load(f)
    if not source_face_data:
        raise RuntimeError(
            "The source-face index is empty. Run a new full process to rebuild it; "
            "do not use Resume with the previous empty index."
        )
    return source_face_data

# ==============================================================================
# --- 5. CORE LOGIC STEPS ---
# ==============================================================================

def step_1_extract_frames(config, log):
    log("--> STEP 1: Extracting frames from video...")
    os.makedirs(config['FRAMES_DIR'], exist_ok=True)
    os.makedirs(config['SWAPPED_FRAMES_DIR'], exist_ok=True)
    video_capture = cv2.VideoCapture(config['TARGET_VIDEO_PATH'])
    if not video_capture.isOpened(): raise Exception(f"Could not open video file at {config['TARGET_VIDEO_PATH']}")
    fps, fps_save = video_capture.get(cv2.CAP_PROP_FPS), config['FRAMES_PER_SECOND_TO_SAVE']
    frames_to_skip = int(fps / fps_save) if fps_save > 0 else 1
    if frames_to_skip == 0: frames_to_skip = 1
    frame_count, saved_frame_count = 0, 0
    while True:
        success, frame = video_capture.read()
        if not success: break
        if frame_count % frames_to_skip == 0:
            cv2.imwrite(os.path.join(config['FRAMES_DIR'], f"frame_{saved_frame_count:05d}.jpg"), frame)
            saved_frame_count += 1
        frame_count += 1
    video_capture.release()
    log(f"    Extracted {saved_frame_count} frames to temp folder.")

def step_2_index_source_faces(config, log):
    log("\n--- STEP 2: Indexing source faces (once for all media) ---")
    progress = config.get('TASK_PROGRESS_CALLBACK')
    source_dir = os.path.abspath(config['SOURCE_IMAGES_DIR'])
    cache_path = config['PERSISTENT_INDEX_PATH']
    force_rebuild = config.get('FORCE_REBUILD_INDEX', False)
    cached_records = {}
    if not force_rebuild and os.path.exists(cache_path):
        try:
            with open(cache_path, 'rb') as f:
                cache = pickle.load(f)
            if (cache.get('version') == 3 and
                    cache.get('source_dir') == source_dir):
                cached_records = cache.get('records', {})
            else:
                log("    Face cache format or source folder changed; rebuilding it.")
        except Exception as e:
            log(f"    Could not read persistent face cache; rebuilding it. Error: {e}")
    elif force_rebuild:
        log("    Forced face-index rebuild requested.")

    source_face_data = []
    new_cache_records = {}
    pending = []
    reused_count = 0
    cached_skip_count = 0
    image_files = sorted(
        f for f in os.listdir(config['SOURCE_IMAGES_DIR'])
        if f.lower().endswith(('.png', '.jpg', '.jpeg')))
    total_images = len(image_files)
    completed_images = 0
    if progress:
        progress(0, f'Indexing source faces: 0 of {total_images}')
    for filename in image_files:
        image_path = os.path.join(config['SOURCE_IMAGES_DIR'], filename)
        try:
            stat = os.stat(image_path)
        except OSError as e:
            log(f"    Warning: Could not inspect {filename}: {e}. Skipping.")
            completed_images += 1
            if progress and total_images:
                progress(completed_images / total_images * 100,
                         f'Indexing source faces: {completed_images} of {total_images}')
            continue
        signature = {'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}
        cached = cached_records.get(filename)
        if (cached and cached.get('size') == signature['size'] and
                cached.get('mtime_ns') == signature['mtime_ns']):
            if cached.get('embedding') is not None:
                record = {'filename': filename, 'embedding': cached['embedding']}
                source_face_data.append(record)
                reused_count += 1
            elif cached.get('status') in ('no_face', 'unreadable'):
                # Remember unchanged failures so hundreds of unsuitable files
                # are not fully scanned again every time the app launches.
                cached_skip_count += 1
            else:
                pending.append((filename, image_path, signature))
                continue
            new_cache_records[filename] = cached
            completed_images += 1
            if progress and total_images:
                progress(completed_images / total_images * 100,
                         f'Indexing source faces: {completed_images} of {total_images}')
        else:
            pending.append((filename, image_path, signature))

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)

    def save_index_checkpoint():
        """Atomically preserve progress so an interrupted run resumes cleanly."""
        cache_temp = cache_path + '.part'
        with open(cache_temp, 'wb') as f:
            pickle.dump({'version': 3, 'source_dir': source_dir,
                         'records': new_cache_records}, f)
        os.replace(cache_temp, cache_path)
        if source_face_data:
            index_temp = config['INDEX_FILE_PATH'] + '.part'
            with open(index_temp, 'wb') as f:
                pickle.dump(source_face_data, f)
            os.replace(index_temp, config['INDEX_FILE_PATH'])

    face_analyzer = None
    fallback_analyzer = None
    if pending:
        try:
            face_analyzer = insightface.app.FaceAnalysis(providers=[config['GPU_PROVIDER']])
            face_analyzer.prepare(ctx_id=0, det_thresh=0.08, det_size=(1024, 1024))
            fallback_analyzer = insightface.app.FaceAnalysis(providers=[config['GPU_PROVIDER']])
            fallback_analyzer.prepare(ctx_id=0, det_thresh=0.03, det_size=(640, 640))
        except Exception as e:
            log(f"    Failed to load analyzer with {config['GPU_PROVIDER']}, falling back to CPU. Error: {e}")
            face_analyzer = insightface.app.FaceAnalysis(providers=['CPUExecutionProvider'])
            face_analyzer.prepare(ctx_id=0, det_thresh=0.08, det_size=(1024, 1024))
            fallback_analyzer = insightface.app.FaceAnalysis(providers=['CPUExecutionProvider'])
            fallback_analyzer.prepare(ctx_id=0, det_thresh=0.03, det_size=(640, 640))

    indexed_count = 0
    skipped_count = 0
    processed_since_checkpoint = 0
    for filename, image_path, signature in pending:
        image = cv2.imread(image_path)
        if image is None:
            log(f"    Warning: Could not read {filename}. Skipping.")
            new_cache_records[filename] = {
                'size': signature['size'],
                'mtime_ns': signature['mtime_ns'],
                'embedding': None,
                'status': 'unreadable',
            }
            skipped_count += 1
            completed_images += 1
            processed_since_checkpoint += 1
            if processed_since_checkpoint >= 25:
                save_index_checkpoint()
                processed_since_checkpoint = 0
            if progress and total_images:
                progress(completed_images / total_images * 100,
                         f'Indexing source faces: {completed_images} of {total_images}')
            continue
        # Try several identity-safe orientations, padded canvases and enhanced
        # variants. Padding is especially important for tightly cropped heads:
        # detectors often reject them when landmarks touch an image boundary.
        # Only the embedding is retained, so transformed landmarks are unused.
        base_passes = [
            ('original', image),
            ('mirrored', cv2.flip(image, 1)),
            ('rotated right', cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)),
            ('rotated left', cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)),
            ('rotated 180', cv2.rotate(image, cv2.ROTATE_180)),
        ]
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        lightness, channel_a, channel_b = cv2.split(lab)
        lightness = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(lightness)
        enhanced = cv2.cvtColor(cv2.merge((lightness, channel_a, channel_b)), cv2.COLOR_LAB2BGR)
        sharpened = cv2.addWeighted(image, 1.6, cv2.GaussianBlur(image, (0, 0), 2.0), -0.6, 0)
        base_passes.extend([
            ('contrast enhanced', enhanced),
            ('sharpened', sharpened),
        ])

        detection_passes = []
        for method, candidate in base_passes:
            detection_passes.append((method, candidate))
            h, w = candidate.shape[:2]
            for fraction in (0.25, 0.50):
                pad_y = max(24, int(h * fraction))
                pad_x = max(24, int(w * fraction))
                # Use the median corner color so black-background portraits
                # receive black padding without reflecting duplicate features.
                corners = np.vstack((
                    candidate[0, 0], candidate[0, -1],
                    candidate[-1, 0], candidate[-1, -1]
                ))
                border_color = tuple(int(v) for v in np.median(corners, axis=0))
                padded = cv2.copyMakeBorder(
                    candidate, pad_y, pad_y, pad_x, pad_x,
                    cv2.BORDER_CONSTANT, value=border_color
                )
                detection_passes.append(
                    (f'{method}, {int(fraction * 100)}% padded', padded)
                )
        faces = []
        detection_method = 'original'
        try:
            for method, candidate in detection_passes:
                faces = face_analyzer.get(candidate)
                if faces:
                    detection_method = method
                    break
            if not faces and fallback_analyzer is not None:
                for method, candidate in detection_passes:
                    faces = fallback_analyzer.get(candidate)
                    if faces:
                        detection_method = f'{method}, low-threshold fallback'
                        break
        except Exception as e:
            log(f"    Warning: Face detection failed for {filename}: {e}. Will retry next run.")
            completed_images += 1
            if progress and total_images:
                progress(completed_images / total_images * 100,
                         f'Indexing source faces: {completed_images} of {total_images}')
            continue
        source_face = select_largest_face(faces)
        if source_face is not None:
            embedding = source_face.normed_embedding
            source_face_data.append({'filename': filename, 'embedding': embedding})
            new_cache_records[filename] = {
                'size': signature['size'],
                'mtime_ns': signature['mtime_ns'],
                'embedding': embedding,
                'status': 'indexed',
            }
            indexed_count += 1
            log(f"    Indexed face from: {filename}")
            if len(faces) > 1:
                log(f"      Detected {len(faces)} candidates; selected the largest face.")
            elif detection_method != 'original':
                log(f"      Face recovered using {detection_method} detection.")
        else:
            log(f"    Warning: Could not detect a usable face in {filename}. Skipping.")
            new_cache_records[filename] = {
                'size': signature['size'],
                'mtime_ns': signature['mtime_ns'],
                'embedding': None,
                'status': 'no_face',
            }
            skipped_count += 1
        completed_images += 1
        processed_since_checkpoint += 1
        if processed_since_checkpoint >= 25:
            save_index_checkpoint()
            processed_since_checkpoint = 0
        if progress and total_images:
            progress(completed_images / total_images * 100,
                     f'Indexing source faces: {completed_images} of {total_images}')
    if not source_face_data:
        raise RuntimeError(
            "No source faces were indexed. Processing was stopped before face matching. "
            "Check that the Source Images Folder contains readable portraits."
        )
    save_index_checkpoint()
    log(f"    Indexing complete: {reused_count} cached, {indexed_count} newly indexed, "
        f"{len(source_face_data)} total faces; {cached_skip_count} cached skips, "
        f"{skipped_count} new skips.")

def step_3_swap_faces(config, log, pause_event, stop_event):
    log("--> STEP 3: Initial Face Swap Pass...")
    source_face_data = load_source_face_index(config['INDEX_FILE_PATH'])
    try:
        face_analyzer = insightface.app.FaceAnalysis(providers=[config['GPU_PROVIDER']])
        face_analyzer.prepare(ctx_id=0, det_size=(640, 640))
        face_swapper = load_face_swapper(config, [config['GPU_PROVIDER']])
        post_chain = load_post_process_chain(config, [config['GPU_PROVIDER']], log)
    except Exception as e:
        if config['GPU_PROVIDER'] == 'CPUExecutionProvider':
            raise RuntimeError(f"Could not load models using CPU: {e}") from e
        log(f"    Failed to load models with {config['GPU_PROVIDER']}, falling back to CPU. Error: {e}")
        face_analyzer = insightface.app.FaceAnalysis(providers=['CPUExecutionProvider'])
        face_analyzer.prepare(ctx_id=0, det_size=(640, 640))
        face_swapper = load_face_swapper(config, ['CPUExecutionProvider'])
        post_chain = load_post_process_chain(config, ['CPUExecutionProvider'], log)
    if config['ENABLE_QUICK_SCAN']:
        haar_cascade_path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
        quick_face_detector = cv2.CascadeClassifier(haar_cascade_path)
        if quick_face_detector.empty(): raise Exception("Failed to load Haar Cascade model for Quick Scan.")
        log("    Quick Scan enabled.")
    
    frame_files = sorted([f for f in os.listdir(config['FRAMES_DIR']) if f.endswith('.jpg')])
    swapped_files = set(os.listdir(config['SWAPPED_FRAMES_DIR']))
    total_frames = len(frame_files)
    progress = config.get('TASK_PROGRESS_CALLBACK')
    
    res_str = config.get('PROCESSING_RESOLUTION', 'Original')
    res_wh = None
    if res_str != 'Original':
        try:
            w, h = map(int, res_str.split('x'))
            res_wh = (w, h)
        except ValueError: log(f"    Invalid resolution string: {res_str}. Defaulting to Original.")
    log(f"    Processing at resolution: {res_str}")
    
    consistency_map = {'Low': 0.05, 'Medium': 0.1, 'High': 0.15, 'Maximum': 0.2}
    consistency_bonus = consistency_map.get(config.get('FACE_CONSISTENCY', 'Medium'), 0.1)
    log(f"    Face Consistency set to: {config.get('FACE_CONSISTENCY', 'Medium')} (Bonus: {consistency_bonus})")

    skipped_frames, processed_frames, last_best_match_index = 0, 0, -1
    for i, frame_filename in enumerate(frame_files):
        if progress and total_frames:
            progress(i / total_frames * 100,
                     f'Generating video frame {i + 1} of {total_frames}')
        while pause_event.is_set(): time.sleep(0.5)
        if stop_event.is_set(): log("    Stop signal received."); return
        if (i + 1) % 25 == 0 or i == total_frames - 1: log(f"    Progress: {i+1} / {total_frames} frames ({(i+1)/total_frames*100:.1f}%)")
        if frame_filename in swapped_files:
            processed_frames += 1; continue
        
        target_img_original = cv2.imread(os.path.join(config['FRAMES_DIR'], frame_filename))
        
        if config['ENABLE_QUICK_SCAN']:
            gray_img = cv2.cvtColor(target_img_original, cv2.COLOR_BGR2GRAY)
            faces_found = quick_face_detector.detectMultiScale(gray_img, 1.1, 4)
            if len(faces_found) == 0:
                output_img = post_chain.finish_frame(target_img_original)
                cv2.imwrite(os.path.join(config['SWAPPED_FRAMES_DIR'], frame_filename), output_img)
                skipped_frames += 1; last_best_match_index = -1; continue
        
        if res_wh:
            original_h, original_w, _ = target_img_original.shape
            target_img = cv2.resize(target_img_original, res_wh, interpolation=cv2.INTER_AREA)
        else: target_img = target_img_original
        
        target_faces = face_analyzer.get(target_img)
        final_img = target_img.copy()
        
        if target_faces:
            for target_face in target_faces:
                distances = [1 - np.dot(target_face.normed_embedding, data['embedding']) for data in source_face_data]
                if last_best_match_index != -1: distances[last_best_match_index] -= consistency_bonus
                best_match_index = np.argmin(distances)
                last_best_match_index = best_match_index
                source_face = indexed_source_face(source_face_data[best_match_index])
                swapped_img = face_swapper.get(final_img, target_face, source_face, paste_back=True)
                swapped_img = post_chain.protect_occlusions(final_img, swapped_img, target_face)
                if config['ENABLE_COLOR_CORRECTION']: final_img = correct_colors(final_img, swapped_img, target_face)
                else: final_img = swapped_img
                final_img = post_chain.process_face(final_img, target_face)
        else: last_best_match_index = -1

        if res_wh: final_img = cv2.resize(final_img, (original_w, original_h), interpolation=cv2.INTER_CUBIC)
        final_img = post_chain.finish_frame(final_img)
        cv2.imwrite(os.path.join(config['SWAPPED_FRAMES_DIR'], frame_filename), final_img)
    
    if processed_frames > 0: log(f"    Resumed process, skipped {processed_frames} already swapped frames.")
    if skipped_frames > 0: log(f"    Quick Scan skipped heavy processing on {skipped_frames} frames.")
    log("    Initial swap pass complete.")
    if progress:
        progress(100, 'Video frame generation complete')

def step_3b_review_and_fix_misses(config, log, pause_event, stop_event):
    log("--> STEP 3b: Review Pass to fix any missed faces...")
    source_face_data = load_source_face_index(config['INDEX_FILE_PATH'])
    try:
        face_analyzer = insightface.app.FaceAnalysis(providers=[config['GPU_PROVIDER']])
        face_analyzer.prepare(ctx_id=0, det_size=(640, 640))
        face_swapper = load_face_swapper(config, [config['GPU_PROVIDER']])
        post_chain = load_post_process_chain(config, [config['GPU_PROVIDER']], log)
    except Exception as e:
        if config['GPU_PROVIDER'] == 'CPUExecutionProvider':
            raise RuntimeError(f"Could not load models using CPU: {e}") from e
        log(f"    Failed to load models with {config['GPU_PROVIDER']}, falling back to CPU. Error: {e}")
        face_analyzer = insightface.app.FaceAnalysis(providers=['CPUExecutionProvider'])
        face_analyzer.prepare(ctx_id=0, det_size=(640, 640))
        face_swapper = load_face_swapper(config, ['CPUExecutionProvider'])
        post_chain = load_post_process_chain(config, ['CPUExecutionProvider'], log)

    frame_files = sorted([f for f in os.listdir(config['FRAMES_DIR']) if f.endswith('.jpg')])
    total_frames = len(frame_files)
    fixed_frames = 0
    
    for i, frame_filename in enumerate(frame_files):
        while pause_event.is_set(): time.sleep(0.5)
        if stop_event.is_set(): log("    Stop signal received."); return
        if (i + 1) % 50 == 0 or i == total_frames - 1: log(f"    Reviewing Progress: {i+1} / {total_frames} frames")
        
        original_img = cv2.imread(os.path.join(config['FRAMES_DIR'], frame_filename))
        swapped_img = cv2.imread(os.path.join(config['SWAPPED_FRAMES_DIR'], frame_filename))

        original_faces = face_analyzer.get(original_img)
        if not original_faces: continue

        swapped_faces = face_analyzer.get(swapped_img)

        if len(original_faces) != len(swapped_faces):
            fixed_frames += 1
            final_img = original_img.copy()
            for target_face in original_faces:
                distances = [1 - np.dot(target_face.normed_embedding, data['embedding']) for data in source_face_data]
                best_match_index = np.argmin(distances)
                source_face = indexed_source_face(source_face_data[best_match_index])
                swapped_result = face_swapper.get(final_img, target_face, source_face, paste_back=True)
                swapped_result = post_chain.protect_occlusions(final_img, swapped_result, target_face)
                if config['ENABLE_COLOR_CORRECTION']: final_img = correct_colors(final_img, swapped_result, target_face)
                else: final_img = swapped_result
                final_img = post_chain.process_face(final_img, target_face)
            final_img = post_chain.finish_frame(final_img)
            cv2.imwrite(os.path.join(config['SWAPPED_FRAMES_DIR'], frame_filename), final_img)

    if fixed_frames > 0:
        log(f"    Review Pass complete. Found and fixed {fixed_frames} frames with missed faces.")
    else:
        log("    Review Pass complete. No missed faces found.")

def step_4_create_final_video(config, log):
    log("--> STEP 4: Creating final video...")
    frame_files = sorted([os.path.join(config['SWAPPED_FRAMES_DIR'], f) for f in os.listdir(config['SWAPPED_FRAMES_DIR']) if f.endswith('.jpg')])
    if not frame_files: raise Exception("No swapped frames found to create video.")
    image_clip = ImageSequenceClip(frame_files, fps=config['FRAMES_PER_SECOND_TO_SAVE'])
    try:
        original_video_clip = VideoFileClip(config['TARGET_VIDEO_PATH'])
        audio_clip = original_video_clip.audio
        final_clip = image_clip.set_audio(audio_clip)
        final_clip.write_videofile(config['FINAL_VIDEO_PATH'], codec='libx264', audio_codec='aac', logger='bar')
        log(f"    Final video successfully created at: {config['FINAL_VIDEO_PATH']}")
    except Exception as e:
        log(f"    Error creating video with audio: {e}. Saving without audio.")
        image_clip.write_videofile(config['FINAL_VIDEO_PATH'], codec='libx264', logger='bar')
        log(f"    Final video (no audio) created at: {config['FINAL_VIDEO_PATH']}")

def swap_single_image(config, log):
    log("--> Swapping face in single image...")
    progress = config.get('TASK_PROGRESS_CALLBACK')
    if progress:
        progress(5, 'Loading face-swap models')
    source_face_data = load_source_face_index(config['INDEX_FILE_PATH'])
    try:
        face_analyzer = insightface.app.FaceAnalysis(providers=[config['GPU_PROVIDER']])
        face_analyzer.prepare(ctx_id=0, det_size=(640, 640))
        face_swapper = load_face_swapper(config, [config['GPU_PROVIDER']])
        post_chain = load_post_process_chain(config, [config['GPU_PROVIDER']], log)
    except Exception as e:
        if config['GPU_PROVIDER'] == 'CPUExecutionProvider':
            raise RuntimeError(f"Could not load models using CPU: {e}") from e
        log(f"    Failed to load models with {config['GPU_PROVIDER']}, falling back to CPU. Error: {e}")
        face_analyzer = insightface.app.FaceAnalysis(providers=['CPUExecutionProvider'])
        face_analyzer.prepare(ctx_id=0, det_size=(640, 640))
        face_swapper = load_face_swapper(config, ['CPUExecutionProvider'])
        post_chain = load_post_process_chain(config, ['CPUExecutionProvider'], log)

    target_img = cv2.imread(config['TARGET_IMAGE_PATH'])
    # For still images, perform the creative edit before swapping the face.
    # This lets Qwen change hair/background while the final face swap restores
    # the selected source identity afterward.
    prompt_applied_before_swap = post_chain.prompt_editor is not None
    if prompt_applied_before_swap:
        if progress:
            progress(10, 'Applying prompt edit before face swap')
        before_prompt = target_img.copy()
        target_img = post_chain.apply_prompt(target_img)
        preview_dir = os.path.join(config['TEMP_DIR'], 'prompt_previews')
        os.makedirs(preview_dir, exist_ok=True)
        preview_name = os.path.splitext(os.path.basename(config['TARGET_IMAGE_PATH']))[0]
        preview_path = os.path.join(preview_dir, f'{preview_name}_before_face_swap.png')
        cv2.imwrite(preview_path, target_img)
        if target_img.shape == before_prompt.shape:
            mean_change = float(np.mean(cv2.absdiff(target_img, before_prompt)))
            log(f'    Prompt edit pixel-change score: {mean_change:.2f}')
            if mean_change < 1.0:
                engine_name = config.get('PROMPT_ENGINE', 'prompt provider')
                log(
                    f'    Warning: {engine_name} returned an almost unchanged image. '
                    'Try another cloud model and a shorter, direct prompt.'
                )
        log(f'    Pre-swap prompt preview saved to: {preview_path}')
    target_faces = face_analyzer.get(target_img)
    final_img = target_img.copy()
    if progress:
        progress(20, 'Detecting target faces')

    if target_faces:
        log(f"    Found {len(target_faces)} face(s) in the image.")
        for face_number, target_face in enumerate(target_faces, 1):
            distances = [1 - np.dot(target_face.normed_embedding, data['embedding']) for data in source_face_data]
            best_match_index = np.argmin(distances)
            source_face = indexed_source_face(source_face_data[best_match_index])
            swapped_img = face_swapper.get(final_img, target_face, source_face, paste_back=True)
            swapped_img = post_chain.protect_occlusions(final_img, swapped_img, target_face)
            if config['ENABLE_COLOR_CORRECTION']: final_img = correct_colors(final_img, swapped_img, target_face)
            else: final_img = swapped_img
            final_img = post_chain.process_face(final_img, target_face)
            if progress:
                progress(20 + face_number / len(target_faces) * 55,
                         f'Swapping face {face_number} of {len(target_faces)}')
    else:
        log("    No faces found in the image. Saving original.")

    if progress:
        progress(80, 'Applying enhancement and prompt stages')
    final_img = post_chain.finish_frame(
        final_img, include_prompt=not prompt_applied_before_swap)
    if progress:
        progress(95, 'Saving generated image')
    cv2.imwrite(config['FINAL_IMAGE_PATH'], final_img)
    log(f"    Swapped image saved to: {config['FINAL_IMAGE_PATH']}")
    if progress:
        progress(100, 'Image generation complete')

# ==============================================================================
# --- 5. MAIN EXECUTION BLOCK ---
# ==============================================================================
def hide_windows_console():
    """Hide the console created by python.exe so only the GUI remains visible."""
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        console_window = ctypes.windll.kernel32.GetConsoleWindow()
        if console_window:
            ctypes.windll.user32.ShowWindow(console_window, 0)
    except Exception:
        # The GUI can still run normally if Windows denies access to the console.
        pass


if __name__ == '__main__':
    hide_windows_console()
    root = tk.Tk()
    app = FaceSwapApp(root)
    root.mainloop()
