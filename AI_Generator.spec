# PyInstaller one-folder build for AI Generator on Windows.
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None
project_root = os.path.abspath(SPECPATH)

datas=[]
binaries=[]
hiddenimports=[
    'model_scanner','texture_scanner','file_scanner','sound_scanner','extract_tool','music_tool',
    'audio_splitter','video_tool','design_tool','research_tool','library_tool','sort_tool','converter_tool','uv_layout_tool',
    'tkinter','tkinter.ttk','PIL.ImageTk','imageio_ffmpeg','moviepy','onnx','onnxruntime',
]

for folder in ('resources','tools','Python'):
    source=os.path.join(project_root,folder)
    if os.path.isdir(source):datas.append((source,folder))

# These packages load providers/pipelines dynamically, so their normal import
# graph is not enough for a frozen build. Missing optional packages are skipped.
for package in ('insightface','onnxruntime','cv2','skimage','sklearn','scipy','moviepy','imageio_ffmpeg','pydub','openai','huggingface_hub','torch','torchvision','diffusers','transformers','accelerate','safetensors','demucs','basic_pitch'):
    try:
        package_datas,package_binaries,package_hidden=collect_all(package)
        datas+=package_datas;binaries+=package_binaries;hiddenimports+=package_hidden
    except Exception:
        try:hiddenimports+=collect_submodules(package)
        except Exception:pass

icon_path=os.path.join(project_root,'resources','AI_Generator.ico')
if not os.path.isfile(icon_path):icon_path=os.path.join(project_root,'icon_resources','AI_Generator.ico')
if not os.path.isfile(icon_path):icon_path=None

a=Analysis(
    ['main.py'],pathex=[project_root],binaries=binaries,datas=datas,
    hiddenimports=sorted(set(hiddenimports)),hookspath=[],hooksconfig={},
    runtime_hooks=[],excludes=[],noarchive=False,optimize=0,
)
pyz=PYZ(a.pure,cipher=block_cipher)
exe=EXE(
    pyz,a.scripts,[],exclude_binaries=True,name='AI Generator',debug=False,
    bootloader_ignore_signals=False,strip=False,upx=False,console=False,
    disable_windowed_traceback=False,argv_emulation=False,
    target_arch=None,codesign_identity=None,entitlements_file=None,icon=icon_path,
)
coll=COLLECT(
    exe,a.binaries,a.datas,strip=False,upx=False,upx_exclude=[],
    name='AI_Generator',
)
