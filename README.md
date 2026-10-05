<img width="902" height="977" alt="pythonw3 13_cUebPXFS0p" src="https://github.com/user-attachments/assets/67b82576-7bfe-4878-9324-8d65002d101a" />
<img width="902" height="977" alt="pythonw3 13_6lwcbrQy1n" src="https://github.com/user-attachments/assets/d739bf94-ce31-4412-a1ad-25ff1eeb795f" />
<img width="902" height="977" alt="pythonw3 13_RMYqqzpIeL" src="https://github.com/user-attachments/assets/f367ac49-4d3c-47fe-a7a0-1af680a24dd7" />
<img width="902" height="977" alt="pythonw3 13_EAr92lqknx" src="https://github.com/user-attachments/assets/2ac3e198-c33c-45d9-b975-3e751387552d" />
<img width="902" height="977" alt="pythonw3 13_vQ7qNznbp8" src="https://github.com/user-attachments/assets/d9aae648-7910-4131-80e1-6a3dc7b0e139" />


# AI Generator

AI Generator is a Windows desktop application for batch face swapping, face restoration, prompt-guided image editing, colorization, upscaling, tone correction, video processing, image review, and cropping.

The interface is designed around a folder-based workflow: place identity portraits in the source folder, place images or videos in the target folder, choose the processing options, and run the complete pipeline.

> Use face-swapping and generative editing only with material you own or have permission to process. Do not use the application for impersonation, deception, harassment, or non-consensual imagery.

## Main features

- Batch processing for images and videos
- Three compatible face-swap model choices, including 128 and 256 input sizes
- Persistent source-face indexing with incremental resume support
- Automatic face matching using InsightFace embeddings
- Multiple ONNX face-restoration models
- Multiple ONNX upscalers and colorization models
- Brightness and gamma correction
- Smart occlusion and face-boundary protection
- Local and cloud prompt-guided image editing
- A2E GPT Image and Qwen editing with 1K or 2K output
- OpenAI-compatible cloud image editing
- Hugging Face Qwen cloud editing
- Local Diffusers prompt editing for supported NVIDIA systems
- Manual image crop editor and batch cropping
- Video quick scan, automatic review pass, manual review, pause/resume, and audio restoration
- Separate task and overall progress bars
- Persistent settings in `config.json`
- Automatic model downloads when a feature is first enabled
- Modern, slightly transparent Windows interface

## Recommended system

- Windows 10 or Windows 11, 64-bit
- 64-bit Python 3.11 recommended; the installer also checks Python 3.12 and `python` on PATH
- 16 GB RAM minimum; 32 GB or more recommended for large batches
- NVIDIA GPU recommended for CUDA processing and local prompt editing
- Current NVIDIA display driver
- Internet connection for installation, automatic model downloads, and cloud prompt engines
- Several gigabytes of free storage for Python packages, ONNX models, temporary video frames, and local Diffusers models

## New-user installation

### 1. Prepare the application folder

Extract the complete package to a normal writable folder, for example:

```text
D:\PROGRAMS\AI_Generator
```

Do not run the application from inside a ZIP file. Confirm that `main.py`, `Setup.bat`, `Run.bat`, and `requirements.txt` are in the same top-level folder.

### 2. Install Python

Install 64-bit Python 3.11 from [python.org](https://www.python.org/downloads/). During installation, enable **Add Python to PATH**.

Verify Python from Command Prompt:

```bat
py -3.11 --version
```

### 3. Run the installer

Double-click `Setup.bat`.

The installer:

1. Finds an available Python installation.
2. Creates a private `.venv` environment inside the application folder.
3. Updates `pip`, `setuptools`, and `wheel`.
4. Installs the packages from `requirements.txt`.
5. Creates the standard application folders.

Wait for **Setup completed successfully** before closing the window.

### 4. Start AI Generator

Double-click `Run.bat`. It launches `main.py` through `pythonw.exe`, so a second Command Prompt window is not left open.

Run `Setup.bat` again only when requirements change, the `.venv` folder is removed, or the Python environment becomes damaged.

## Standard folder layout

```text
AI_Generator\
├─ main.py
├─ Setup.bat
├─ Run.bat
├─ requirements.txt
├─ config.json                 Generated after settings are saved
├─ .venv\                     Private Python environment
├─ models\                    ONNX models and persistent face indexes
├─ resources\                 Discord.png, Patreon.png and PayPal.png
├─ source\                    Source identity portraits
├─ target\                    Target images and videos
├─ result\                    Finished outputs
└─ temp_processing\           Frames, working files and prompt previews
```

Folder paths can be changed from the **Paths** tab. The names above are the defaults created by `Setup.bat`.

## Quick start

1. Place clear portraits of the identity to copy in `source`.
2. Place the images or videos to modify in `target`.
3. Start AI Generator with `Run.bat`.
4. Confirm the four paths on the **Paths** tab.
5. On **Face Swap**, select the GPU provider and swapper model.
6. Choose optional restoration, colorization, upscaling, tone, or prompt-editing features.
7. Click **Run Full Process**.
8. Finished files are written to `result` or the selected output folder.

Output names include the target name and source-folder name so batches from different identities remain distinguishable.

## Paths tab

| Setting | Purpose |
|---|---|
| Source images | Portraits used to build identity embeddings. |
| Target media | Images and videos that receive the face swap. |
| Output folder | Final processed images and videos. |
| Temporary folder | Extracted frames, prompt previews, working indexes, and interrupted video data. |

Supported source formats are PNG, JPG, and JPEG. The target processor supports common image formats and video formats readable by OpenCV/MoviePy.

## Face Swap tab

### GPU provider

- **CUDAExecutionProvider** — recommended for a compatible NVIDIA GPU.
- **DmlExecutionProvider** — DirectML option for supported Windows GPUs.
- **CPUExecutionProvider** — slow fallback when GPU execution is unavailable.

If the selected GPU provider fails while loading a model, the program attempts a CPU fallback.

### Swapper models

| Interface option | File | Use |
|---|---|---|
| inswapper 128 Quality | `inswapper_128.onnx` | Standard compatibility and quality. |
| inswapper 128 FP16 Speed | `inswapper_128_fp16.onnx` | Faster/lighter FP16 processing. |
| reswapper 256 Quality | `reswapper_256.onnx` | Higher 256-pixel face input when using the original InswapperClass-compatible build. |

Do not substitute an arbitrary 256 ONNX file. `reswapper_256.onnx` must be the original InswapperClass-compatible build expected by the program.

### Processing resolution

- **Original** preserves the target dimensions during face processing.
- **1280×720** and **854×480** reduce video workload and improve speed.

Use **Original** for still-image quality and when final resolution matters most.

### Face consistency

Low, Medium, High, and Maximum adjust how strictly target faces are matched to indexed source identities. Higher settings can improve identity consistency but may reject more uncertain matches.

### Face-swap checkboxes

- **Enable color correction** — adjusts the swapped face toward the target image's color and lighting.
- **Enable quick scan** — uses a lightweight detector to skip expensive video-frame processing where no face is likely present.
- **Enable review pass** — examines processed video frames and repairs likely missed swaps.
- **Enable manual review mode** — keeps processed frames available for review before final video creation.
- **Rebuild face index this run** — ignores the persistent cache and rescans every source image.
- **Reprocess existing outputs** — replaces outputs that would otherwise be skipped because their filenames already exist.

## Persistent source-face indexing

Source portraits are indexed once and cached as:

```text
models\source_faces_<folder-hash>.pkl
```

The cache stores embeddings, source filenames, file sizes, modification times, and remembered detection failures. On later launches:

- Unchanged successful portraits are reused immediately.
- New or modified portraits are indexed.
- Unchanged unreadable/no-face images are skipped without repeating full detection.
- A checkpoint is saved every 25 newly processed files, allowing a large index to continue after interruption.

Indexing tries the original image, mirrored orientation, 90/180-degree rotations, and a contrast-enhanced pass. If several faces are found, the largest face is selected.

Use **Rebuild face index this run** after intentionally replacing many source files, changing their contents without updating timestamps, or troubleshooting a corrupted cache.

### Good source portraits

- One clearly visible face
- Face large enough to identify
- Sharp eyes and facial features
- Reasonable lighting and contrast
- Limited obstruction from hands, hair, sunglasses, or extreme angles
- A useful range of front, three-quarter, profile, upward, and downward angles

## Enhance tab

### Face restoration

| Option | Model file | Typical use |
|---|---|---|
| CodeFormer | `codeformer_fp16.onnx` | Balanced cleanup and facial-detail restoration. |
| GFPGAN 1024 | `gfpgan-1024.onnx` | Strong 1024-pixel face restoration. |
| RestoreFormer++ | `RestoreFormerPlusPlus.fp16.onnx` | Alternative restoration for damaged or soft faces. |
| GPEN 512 | `GPEN-BFR-512.onnx` | Lighter GPEN restoration. |
| GPEN 1024 | `GPEN-BFR-1024.onnx` | Higher-resolution GPEN restoration. |

The **Restoration strength** slider shows an exact percentage. Start around 25–35%. Excessive restoration can change identity, create artificial skin, or exaggerate facial details.

### Colorization

- **Off** — no colorization.
- **ColorizeStable** — ONNX colorization using `ColorizeStable.fp16.onnx`.
- **DDColor Natural** — natural colorization using `ddcolor.onnx`.
- **DDColor Artistic** — stronger artistic colorization using `ddcolor_artistic.onnx`.

Colorization is intended mainly for grayscale or faded images. Enabling it on already-correct color images can shift skin, hair, and clothing colors.

### Upscaling

| Option | Model file | Character |
|---|---|---|
| RealESRGAN | `RealESRGAN_x4plus.fp16.onnx` | General photographic enhancement. |
| UltraSharp | `4x-UltraSharp.fp16.onnx` | Strong edges and sharper texture. |
| UltraMix Smooth | `4x-UltraMix_Smooth.fp16.onnx` | Smoother enlargement with fewer harsh edges. |

Select **2×** or **4×** as the upscale factor. Upscaling increases dimensions and processing time; it cannot restore details that were completely absent from the source.

### Brightness and gamma

- **Brightness** ranges from -100 to +100. Positive values brighten; negative values darken.
- **Gamma** ranges from 0.20 to 3.00. Values below 1 generally brighten midtones; values above 1 darken midtones.

Apply small adjustments first to avoid clipped highlights, crushed shadows, or washed-out skin.

### Smart masking

Smart occlusion and face-boundary protection combines:

- `occluder.onnx`
- `faceparser_resnet34.onnx`
- `XSeg_model.onnx`

It helps protect hair, hands, glasses, foreground objects, and the transition around the swapped face. It costs additional processing time.

## Prompt Edit tab

Prompt editing is optional. For still images it runs **before** the final face swap. This allows the creative editor to change hair, clothing, or background while the later face swap restores the chosen source identity.

The program saves a diagnostic preview before face swapping:

```text
temp_processing\prompt_previews\<target-name>_before_face_swap.png
```

Use this preview to determine whether a cloud/local editor made the requested change before restoration and swapping.

### A2E

A2E is recommended for results closest to the A2E web editor.

Available models:

- `gpt-image-2.5-sunburst` — recommended default
- `gpt-image-2.5-flare`
- `gpt-image-2`
- `gpt-image-1.5`
- `qwen-image-3.0-pro`
- `qwen-image-3.0`
- `qwen-image-2.0-pro`
- `qwen-image-2.0`

Available resolution settings are 1K and 2K. Qwen 2K output requires `qwen-image-3.0-pro`. A2E GPT Image models use the selected A2E resolution directly.

To configure A2E:

1. Revoke any token accidentally exposed in a screenshot or public file.
2. Create a new token at [A2E API Token](https://video.a2e.ai/account/token).
3. Run `Configure_A2E_API_Token.bat`.
4. Paste the token. The secure prompt intentionally displays no characters.
5. Completely close and reopen AI Generator.
6. Select **A2E**, `gpt-image-2.5-sunburst`, and **2K**.

The token is stored in the Windows user environment as `A2E_API_TOKEN`; it is not written to `main.py` or `config.json`. A2E processing consumes account credits.

### Cloud

The Cloud engine uses the OpenAI-compatible image edit client and the selected Cloud model/quality.

1. Run `Configure_Cloud_API_Key.bat`.
2. Enter the API key at the hidden prompt.
3. Close and reopen AI Generator.
4. Select **Cloud** and choose a model and quality.

Cloud usage can incur API charges. Never distribute your configured token or place it in source control.

### Qwen Cloud

Qwen Cloud routes Qwen Image Edit through Hugging Face Inference Providers.

1. Create a Hugging Face token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
2. Run `Configure_HuggingFace_Token.bat`.
3. Close and reopen AI Generator.
4. Select **Qwen Cloud** and a Qwen model.

The application measures the returned pixel change and automatically retries with a stronger instruction if the first result is almost unchanged. Provider availability and behavior can vary; A2E is the recommended alternative when this route returns a no-op result.

### Local

The Local engine uses Diffusers on the local system.

1. Complete `Setup.bat`.
2. Run `Install_NVIDIA_Prompt.bat`.
3. Confirm the NVIDIA driver and CUDA-compatible packages are working.
4. Select **Local** in the Prompt Edit tab.

The local model may download several gigabytes on first use. Local prompt editing is slower, uses substantial VRAM, and may not match modern cloud editors for reference preservation or prompt accuracy.

### Writing effective edit prompts

Use one direct, visible instruction and describe what must remain unchanged.

```text
Change her visible hair to natural jet black. Preserve her face, pose,
expression, clothing, lighting, framing, and background.
```

For a hairstyle:

```text
Change her hair to long jet-black hair braided into two symmetrical pigtails.
Preserve her identity, face, pose, expression, clothing, and background.
```

Very tight face crops do not contain enough canvas area for long hair or pigtails. Use a wider portrait when the requested hairstyle must extend below the shoulders.

### Negative prompt

Use the negative prompt sparingly. An overly restrictive negative prompt can cause the editor to preserve the original image or resist the requested change. For A2E GPT edits, a short positive prompt often works better.

### Steps

The Local/Qwen steps control ranges from 10 to 50. Higher values generally take longer. Cloud services may use their own internal settings.

### Video prompts

Enable **Apply to video frames** only when needed. Editing every frame is slow and can introduce temporal flicker because each frame is generated independently.

## Crop tab

### Manual crop editor

Open one image, drag the crop rectangle, preview the selected pixel dimensions, and save a new cropped copy.

### Batch crop

Choose an input folder and output folder, then select:

- **Aspect ratio** — 1:1, 4:5, 3:4, 2:3, 16:9, or 9:16.
- **Exact size** — width and height from 16 to 8192 pixels.
- **Overwrite existing files** — replace matching output files instead of skipping them.

Batch cropping uses image-aware center cropping for each file rather than assuming that every source belongs to a fixed contact-sheet grid.

## Video workflow

1. Frames are extracted to a video-specific temporary folder.
2. Source faces are loaded from the persistent index.
3. Faces are detected, matched, swapped, masked, restored, and enhanced.
4. The optional review pass repairs likely missed frames.
5. Manual review can be used before final rendering.
6. MoviePy rebuilds the video and restores the original audio when available.
7. Temporary frames are removed after successful automatic completion.

The default saved processing rate is 15 frames per second. Long videos can require substantial temporary storage.

## Progress and controls

- **Current task** shows progress for the active operation, including indexing and the current media file.
- **Overall** shows progress across all selected target media.
- **Run Full Process** starts indexing and processing.
- **Create Videos** rebuilds videos from existing processed frame folders.
- **Review** opens manual review/correction tools.
- **Clear Temp** removes disposable working data.
- **Stop** requests a safe stop after the current operation reaches a stopping point.

The interface displays the latest issue instead of a large activity-log panel.

## Model downloads

Required ONNX files download automatically only when the associated option is enabled. Keep ONNX files in `models`.

If a download is interrupted:

1. Close AI Generator.
2. Remove only the incomplete model file.
3. Reopen the application and enable the feature again.

Do not rename models unless the corresponding filename in `main.py` is also intentionally changed.

## Recommended quality settings

For high-quality still images on an NVIDIA P5000:

```text
GPU provider: CUDAExecutionProvider
Swapper: reswapper_256.onnx (256 Quality)
Processing resolution: Original
Face consistency: High
Color correction: On
Face restoration: CodeFormer
Restoration strength: 25–35%
Smart masking: On when hair, hands or glasses cross the face
A2E model: gpt-image-2.5-sunburst
A2E resolution: 2K
Upscaling: Off during testing; enable 2× after the pipeline is correct
```

Test one image before running a large batch. Cloud prompt editing and high-resolution upscaling can consume considerable time or credits across hundreds of files.

## Troubleshooting

### No source faces were indexed

- Confirm the source path is correct.
- Confirm it contains readable PNG/JPG/JPEG portraits.
- Use larger, sharper faces with less obstruction.
- Enable **Rebuild face index this run** after correcting the files.
- Do not use Resume with an empty index.

### Only part of a large source folder is indexed

The index saves every 25 files. Restarting should reuse completed records and continue with new or changed files. If it repeatedly stops at the same file, inspect that image for corruption or an unsupported encoding.

### `attempt to get argmin of an empty sequence`

The source index contained no usable embeddings. The current build stops earlier with a clearer empty-index error. Rebuild the index with valid source portraits.

### Black squares in results

Common causes include an incompatible ONNX model, incorrect tensor type/layout, a restoration model being applied with the wrong preprocessing, or an excessively strong restoration blend.

- Disable all Enhance options and test face swapping alone.
- Re-enable one enhancement at a time.
- Confirm each model has the exact expected filename and build.
- Lower restoration strength.
- Delete and redownload a possibly incomplete model.

### ONNX expected `tensor(double)` but received `tensor(float)`

The model expects float64 input. Use the current model adapter or a compatible model build; do not assume all ONNX files share the same input type.

### Prompt result is unchanged

1. Enable **Reprocess existing outputs**.
2. Inspect `temp_processing\prompt_previews`.
3. Use a short, direct prompt.
4. Reduce or clear the negative prompt.
5. For A2E, select `gpt-image-2.5-sunburst` rather than a Qwen model.
6. Confirm the account has credits and the token is enabled.

If the pre-swap preview changed but the finished output did not, disable restoration and masking temporarily to identify the later stage affecting the result.

### API token appears as one asterisk

This is normal for the secure BAT prompts. They intentionally do not display the actual token length. Paste once, press Enter, then completely close and reopen AI Generator.

### API token exposed in a screenshot

Immediately revoke/delete it in the provider dashboard and create a new token. Never reuse an exposed secret.

### CUDA is unavailable

- Update the NVIDIA driver.
- Run `Setup.bat` again.
- Confirm `onnxruntime-gpu` installed in `.venv`.
- Select `CPUExecutionProvider` temporarily to verify the rest of the application.
- Local Diffusers may require the CUDA-specific PyTorch installation performed by `Install_NVIDIA_Prompt.bat`.

### Bottom controls are cut off

Maximize the window or use a Windows display scaling setting that leaves enough vertical space. The current interface uses a larger initial window and resizable tab layout.

### Existing outputs are skipped

Enable **Reprocess existing outputs** on the Face Swap tab.

## Updating an existing installation

1. Close AI Generator.
2. Back up the current `main.py`.
3. Replace it with the new `main.py`.
4. Keep `models`, `resources`, source images, targets, results, and face-index caches.
5. Run `Setup.bat` if `requirements.txt` changed.
6. Start with `Run.bat`.

Delete or rename `config.json` only when you want all GUI settings reset to defaults.

## Clean distribution and GitHub publishing

Include:

- `main.py`
- `README.md`
- `Setup.bat`
- `Run.bat`
- `Install_NVIDIA_Prompt.bat`
- API-token configuration BAT files
- `requirements.txt`
- Required non-personal resource icons
- Placeholder files such as `.gitkeep` when GitHub must retain empty folders

Do not distribute:

- `.venv`, `Lib`, `Scripts`, `Include`, or `pyvenv.cfg`
- `config.json` containing personal paths
- Source, target, result, or temporary images
- `source_faces_*.pkl` identity caches
- Downloaded ONNX models unless their licenses explicitly allow redistribution
- API keys, environment exports, tokens, logs, or screenshots containing secrets

Git does not store empty directories. Add a `.gitkeep` file to an otherwise empty `models`, `source`, `target`, `result`, `resources`, or `temp_processing` folder when the directory must appear in the repository.

## Installed Python packages

The supplied requirements include:

- NumPy below version 2
- OpenCV
- ONNX Runtime GPU and ONNX
- InsightFace
- MoviePy
- Requests
- tqdm
- Pillow
- OpenAI client
- Hugging Face Hub client
- scikit-image, scikit-learn, and SciPy

## Privacy and security

- Tokens belong in Windows user environment variables, not source files.
- Never commit `config.json`, personal images, face embeddings, or secrets.
- Cloud prompt engines upload selected images to their providers for processing.
- Review each provider's pricing, privacy policy, retention policy, and acceptable-use terms before processing sensitive media.
- Keep backups of original images; generated output should not be treated as the only copy.

## Support links

The bottom-right icon buttons open the configured Patreon, Discord, and PayPal support pages. Their icon files belong in `resources` as:

Paypal
https://www.paypal.com/paypalme/GameModNation
Patreon
https://www.patreon.com/c/3dmodelserver
Join the Discord
https://discord.com/invite/sMZuNzhmxC

