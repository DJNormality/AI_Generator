<img width="902" height="1035" alt="python_x8ypz3SOkS" src="https://github.com/user-attachments/assets/1c6eef73-523a-46de-a636-8e97f4f5a12d" />

# AI Generator

AI Generator is a Windows desktop application for batch face replacement, image and video processing, face restoration, colorization, upscaling, prompt-guided image editing, cropping, and batch file renaming.

It began as a fork of Smart Face Swapper and has been expanded with a modern tabbed interface, persistent source-face indexing, multiple restoration and upscaling models, local and cloud prompt editors, processing progress displays, and utility tools.

## Main Features

### Face replacement

- Batch-process image and video folders.
- Detect and replace one or more faces in each target.
- Choose the closest indexed source face automatically.
- Use the original InsightFace-compatible 128 model, FP16 128 model, or compatible ReSwapper 256 model.
- Processing-resolution and face-consistency controls.
- Optional color correction.
- Quick scan, review pass, and manual review options.
- Pause, resume, stop, and reprocess-existing controls.
- NVIDIA, DirectML, and CPU execution options, depending on installed providers.

### Persistent source-face indexing

- Source faces are indexed once and stored for later sessions.
- Unchanged source folders reuse their existing index.
- New or changed source images can be added without discarding completed work.
- A **Rebuild face index this run** option forces a clean index when necessary.
- Indexing and overall progress are displayed as green progress bars with percentages.
- More forgiving face-detection passes improve recognition of angled, small, or difficult portraits.

Persistent indexes are stored as:

    models/source_faces_*.pkl

These files contain data derived from personal source images. Remove them before distributing a clean copy of the application.

### Face restoration

Supported restoration choices:

- CodeFormer
- GFPGAN 1024
- RestoreFormer++
- GPEN 512
- GPEN 1024

Restoration strength has a visible percentage readout in the interface.

### Colorization

- ColorizeStable
- DDColor Natural
- DDColor Artistic

### Upscaling and sharpening

- RealESRGAN x4
- 4x UltraSharp
- 4x UltraMix Smooth
- 2x and 4x output options

### Tone correction

- Brightness adjustment from -100 to +100.
- Gamma adjustment from 0.20 to 3.00.
- Tone correction can be combined with restoration, colorization, and upscaling.

### Smart face-boundary protection

The optional smart-mask stage combines:

- Occluder
- FaceParser
- XSeg

This helps protect hair, glasses, hats, face boundaries, and foreground obstructions while compositing a swapped face.

## Prompt Editing

Prompt editing is applied before the final face replacement for still images. This lets an editor change hair, clothing, glasses, makeup, pose, or background, after which the face swap restores the selected identity.

Example:

    Change her hair to long black hair fully braided into pigtails.

Prompt editing for every video frame is optional because it is slow and may flicker between frames.

### A2E

- Uses the official A2E REST API.
- Supports Nano Banana, GPT Image, and Qwen choices exposed by A2E.
- Supports 1K and 2K output selections.
- Saves a redacted diagnostic file when a task fails.
- Requires an A2E token configured with `Configure_A2E_API_Token.bat`.
- Uses online credits.

### Local

- Uses `timbrooks/instruct-pix2pix`.
- Runs through PyTorch and Diffusers on an NVIDIA GPU.
- Uses FP16, attention slicing, and VAE slicing.
- Processes a reduced working image and restores the original dimensions afterward.
- Does not require credits after the model has been downloaded.

### Qwen 2.1 Local

- Uses the complete `Qwen/Qwen-Image-2.1` Diffusers pipeline.
- Supports reference-preserving prompt-based image editing.
- Uses FP16 on the Quadro P5000 instead of the model's native BF16 configuration.
- Uses sequential CPU offload, attention slicing, VAE slicing, and VAE tiling.
- Limits the working image to 768 pixels on its longest side to reduce VRAM usage.
- Restores the original image dimensions after editing.
- Keeps the model cached between edits during a session.
- Can load from a Hugging Face model ID or a complete local folder.

The complete Qwen Image 2.1 repository is approximately 33 GB. The `text_encoder` folder alone is not enough. The local folder must contain:

    models/Qwen-Image-2.1/
    ├── model_index.json
    ├── processor/
    ├── scheduler/
    ├── text_encoder/
    ├── transformer/
    └── vae/

In the GUI, select **Qwen 2.1 Local** and enter:

    D:\PROGRAMS\AI_Generator\models\Qwen-Image-2.1

Alternatively, leave the model field as:

    Qwen/Qwen-Image-2.1

The Hugging Face model ID downloads into the normal Hugging Face cache on first use. A complete cached model can be used offline afterward.

The Quadro P5000 configuration is expected to be slow. A single edit may take several minutes.

### Cloud

- Uses the OpenAI Images API.
- Supports the Cloud model and quality choices displayed in the GUI.
- Requires `OPENAI_API_KEY`, configured with `Configure_Cloud_API_Key.bat`.
- Uses online API credits.

### Qwen Cloud

- Uses Qwen Image Edit through Hugging Face Inference Providers.
- Includes retry logic when a provider returns an almost unchanged image.
- Requires `HF_TOKEN`, configured with `Configure_HuggingFace_Token.bat`.
- Provider availability and charges depend on the Hugging Face account.

## Crop Tools

### Manual crop editor

- Open an individual image.
- Drag a crop rectangle directly over the preview.
- Save the selected area as a new file.
- Preserves PNG transparency.

### Batch crop

- Crop an entire directory.
- Choose common aspect ratios.
- Enter an exact output width and height.
- Control whether existing output files are overwritten.

## Batch Renamer

- Rename images, videos, or all supported files.
- Find and replace text in filenames.
- Add prefixes and suffixes.
- Add sequential numbers with selectable starting value and digit count.
- Optionally include subfolders.
- Preview every old and new filename before applying changes.
- Uses temporary names internally to avoid collisions.

## Interface Improvements

- Application renamed to **AI Generator**.
- Modern dark tabbed interface.
- Slightly transparent main window.
- Rounded controls and buttons.
- Green indexing, task, and overall progress bars with percentages.
- No permanent activity-log panel occupying the interface.
- Larger startup window so bottom controls remain visible.
- Customizable application icon from `resources/AI_Generator.ico` or `resources/AI_Generator.png`.
- Icon-only Patreon, Discord, and PayPal buttons at the bottom-right.
- Support artwork is loaded from:

    resources/Patreon.png
    resources/Discord.png
    resources/PayPal.png

- Settings are saved between sessions in `config.json`.
- `Run.bat` uses `pythonw.exe` so the GUI does not keep a separate Command Prompt window open.

## System Requirements

Recommended:

- Windows 10 or Windows 11, 64-bit
- Python 3.13, 64-bit
- 64 GB system RAM for Qwen Image 2.1 Local
- NVIDIA Quadro P5000 or newer GPU
- Current NVIDIA display driver
- At least 40 GB of free disk space for Qwen Image 2.1 alone
- Additional space for ONNX models, Hugging Face caches, temporary frames, and results
- Internet access for initial setup and model downloads

Cloud prompt engines always require internet access.

## First-Time Installation

1. Extract the complete AI Generator folder. Do not run it from inside a ZIP.
2. Install 64-bit Python 3.13.
3. During Python installation, enable **Add Python to PATH** and install the Python launcher.
4. Place the newest setup files beside `main.py`.
5. Run `Setup.bat`.
6. Wait for **Setup completed successfully**.
7. Run `Run.bat`.

The Python environment is installed directly into the AI Generator directory. It creates:

    Include/
    Lib/
    Scripts/
    pyvenv.cfg

The current setup does not use a `.venv` folder.

Setup also applies these Python 3.13 compatibility requirements:

- `setuptools==81.0.0` for current CUDA PyTorch compatibility.
- NumPy 2.x for Python 3.13.
- Precompiled `ml_dtypes==0.6.0` to avoid the failed `share.h` source build.

### Microsoft C++ Build Tools

Some Python packages may require Microsoft C++ Build Tools. Install the **Desktop development with C++** workload, including the MSVC x64/x86 compiler and Windows SDK.

Official installer:

https://visualstudio.microsoft.com/visual-cpp-build-tools/

## Installing NVIDIA Prompt Support

After `Setup.bat` completes, run:

    Install_NVIDIA_Prompt.bat

This installs:

- CUDA-enabled PyTorch and TorchVision
- Transformers 5.17 or newer
- Accelerate
- Safetensors
- SentencePiece
- A current Diffusers build with Qwen Image 2.1 support

## Downloading Qwen 2.1 from a Hugging Face Bucket

For the private bucket `Normality1/Qwen-Image-2.1-bucket`, open Command Prompt inside:

    D:\PROGRAMS\AI_Generator

If `Scripts\hf.exe` still points to an old `.venv`, recreate its launcher:

    Scripts\python.exe -m pip install --force-reinstall --no-cache-dir huggingface_hub

Log in:

    Scripts\hf.exe auth login

Download the complete bucket:

    Scripts\hf.exe buckets sync hf://buckets/Normality1/Qwen-Image-2.1-bucket "models\Qwen-Image-2.1"

The sync command can be run again after interruption. It compares the bucket and local directory and transfers only missing or changed files.

## Application Folders

| Folder or file | Purpose |
| --- | --- |
| `source/` | Source identity portraits |
| `target/` | Target images and videos |
| `result/` or configured output | Finished media |
| `models/` | ONNX models, persistent face indexes, and optional local Qwen model |
| `resources/` | GUI icons and support-button images |
| `temp_processing/` | Temporary frames, prompt previews, and diagnostics |
| `Lib/` | Main-directory Python packages |
| `Scripts/` | Python executables and command-line launchers |
| `pyvenv.cfg` | Identifies the main folder as the Python environment |
| `config.json` | Saved local GUI settings |

## Supported Swapper Models

| GUI choice | Expected file |
| --- | --- |
| InsightFace 128 Quality | `inswapper_128.onnx` |
| InsightFace 128 FP16 Speed | `inswapper_128_fp16.onnx` |
| ReSwapper 256 Quality | `reswapper_256.onnx` |

`reswapper_256.onnx` must be the original InsightFace/Inswapper-class-compatible build. An unrelated ONNX file renamed to `reswapper_256.onnx` will not work.

## Automatic Model Downloads

When a supported ONNX feature is enabled and its model is missing, AI Generator downloads the configured model into `models/`. Keep the original filenames because the loader uses them to select preprocessing and output behavior.

## Clean Distribution

Before sharing or publishing the application, do not include:

- Personal files from `source/`, `target/`, `result/`, or `temp_processing/`
- `config.json`
- API keys or access tokens
- `source_faces_*.pkl`
- `.venv/`
- `Lib/`
- `Scripts/`
- `Include/`
- `pyvenv.cfg`
- Hugging Face cache directories
- Private Qwen model files unless their license permits redistribution

New users should generate their own Python environment with `Setup.bat`.

Never place API keys directly in `main.py`, `config.json`, screenshots, ZIP archives, or the GitHub repository.

## Troubleshooting

### Failed to locate pyvenv.cfg

Run the newest `Setup.bat`. It detects an incomplete main-directory environment and recreates the missing `pyvenv.cfg`.

### A launcher still references .venv

Old executable launchers can retain the path where they were originally created. Reinstall the affected package through the active Python executable:

    Scripts\python.exe -m pip install --force-reinstall --no-cache-dir PACKAGE_NAME

For the Hugging Face CLI:

    Scripts\python.exe -m pip install --force-reinstall --no-cache-dir huggingface_hub

### setuptools conflict with PyTorch

Repair it with:

    Scripts\python.exe -m pip install --upgrade "setuptools==81.0.0"

### ml_dtypes fails while compiling share.h

Install the Python 3.13 wheel:

    Scripts\python.exe -m pip install --upgrade --no-cache-dir --only-binary=:all: "numpy>=2,<3" "ml_dtypes==0.6.0"

### Microsoft Visual C++ 14.0 or greater is required

Install Microsoft C++ Build Tools with **Desktop development with C++**, then restart Windows and rerun `Setup.bat`.

### Qwen 2.1 does not load

Confirm the selected folder contains `model_index.json` and all five required component directories. Rerun the bucket sync to restore missing files.

Also rerun:

    Install_NVIDIA_Prompt.bat

### CUDA is unavailable

- Update the NVIDIA display driver.
- Confirm CUDA-enabled PyTorch was installed.
- Run:

      Scripts\python.exe -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No CUDA GPU')"

### A source folder indexes zero faces

- Use clear, well-lit source portraits.
- Make the face large enough in the frame.
- Avoid heavy blur and extreme occlusion.
- Enable the review pass.
- Select **Rebuild face index this run** after changing the source folder.
- Remove an obsolete or invalid `source_faces_*.pkl` only when rebuilding.

### attempt to get argmin of an empty sequence

No usable source faces were indexed. Fix the source-face detection problem and rebuild the index before processing targets.

### Black squares or damaged output

- Disable restoration, colorization, upscaling, and smart masking temporarily.
- Test face swapping alone.
- Re-enable one post-processing stage at a time.
- Confirm each ONNX file matches the exact expected model rather than only having the expected filename.

### Prompt result is unchanged

- Confirm **Enable prompt editing** is selected.
- Confirm the desired prompt engine is selected.
- Use a direct instruction describing only the requested change.
- Check `temp_processing/prompt_previews/` to see the image produced before face swapping.
- For A2E, inspect the redacted `a2e_last_task.json` diagnostic.
- Remember that the final face swap intentionally restores facial identity after the prompt edit.

## Privacy and Responsible Use

Only process media you own or have permission to edit. Follow applicable privacy, identity, copyright, model-license, and platform rules. Clearly label synthetic or altered media when appropriate.

## Support Links

- Patreon: https://www.patreon.com/c/3dmodelserver
- Discord: https://discord.com/invite/sMZuNzhmxC
- PayPal: https://www.paypal.com/paypalme/GameModNation?country.x=US&locale.x=en_US

