<img width="902" height="793" alt="pythonw3 13_SJXMcRoX9w" src="https://github.com/user-attachments/assets/06fd2c9c-4162-41e4-b57e-c55da22e586b" />
<img width="902" height="793" alt="pythonw3 13_J7IeEc7Fnn" src="https://github.com/user-attachments/assets/ded684ca-c35f-4a5f-8c27-afb2c3ab2cf6" />
<img width="902" height="793" alt="pythonw3 13_B9ASEazSJS" src="https://github.com/user-attachments/assets/7dd28d95-2537-4e43-9c70-f803702b7522" />
<img width="902" height="793" alt="pythonw3 13_5Hd1WoF13H" src="https://github.com/user-attachments/assets/e2daa371-4676-4504-b6de-a422c99eb100" />


AI Generator

100% Free AI Generator tool for enhancing, upscaling, editing, images and videos

Features
- Renamed the program from Smart Face Swapper to AI Generator
- Rebuilt the interface with a modern dark theme
- Added slight window transparency
- Added rounded buttons and controls
- Improved text contrast and readability
- Reorganized settings into tabs:
  - Paths
  - Face Swap
  - Enhance
  - Prompt Edit
- Fixed the initial window size so bottom controls remain visible
- Added automatic window sizing and screen centering
- Removed the large activity-log box
- Replaced logging with a compact status message
- Added green progress bars:
  - Current-task progress and percentage
  - Overall batch progress and percentage
  - Source-face indexing progress
  - Per-image and video-frame generation progress
- Added modern Pause, Resume, Stop, Review, Create Videos, and Clear Temp buttons
Support buttons
- Added Patreon, Discord, and PayPal links
- Replaced their text with icon images
- Added built-in fallback icons if the PNG files are missing
- Moved icon files into the resources folder:
  - resources\Patreon.png
  - resources\Discord.png
  - resources\PayPal.png
- Moved the support-button group to the bottom-right corner
Console behavior
- Added Windows console hiding so the GUI can open without leaving a Command Prompt window visible
- Added compatibility with launching through pythonw.exe
Face-swapping improvements
- Added support for the compatible 256×256 reswapper_256.onnx
- Added model-input-size validation to catch incompatible Reswapper builds
- Retained support for:
  - inswapper_128.onnx
  - inswapper_128_fp16.onnx
- Improved source-face selection when multiple faces are detected
- Selects the largest detected source face instead of rejecting images containing multiple detections
- Reduced the source detection threshold
- Increased source-face detection resolution to 1024×1024
- Added mirrored-image detection as a fallback for difficult or angled portraits
- Added safer handling when no source faces can be indexed
- Prevented the argmin of an empty sequence crash
- Added clearer errors for empty or invalid source-face indexes
Persistent face indexing
- Added persistent source-face caching
- Saves indexed face embeddings as source_faces_*.pkl inside models
- Reuses unchanged indexed faces between program launches
- Detects changed files using filename, size, and modification time
- Only re-indexes new or modified source images
- Added a Rebuild Face Index This Run option
- Added atomic .part writes to reduce the chance of corrupted index files
- Added cached/new/total indexing counts
Face-restoration models
Added selectable support for:
- CodeFormer
- GFPGAN 1024
- RestoreFormer++
- GPEN-BFR 512
- GPEN-BFR 1024
Also added adjustable restoration strength.
Upscaling and sharpening
Added selectable support for:
- RealESRGAN x4
- 4x-UltraSharp
- 4x-UltraMix Smooth
Added selectable output scaling:
- Off
- 2×
- 4×
The enhancement chain now applies restoration and correction before final upscaling.
Colorization
Added selectable colorization modes:
- Off
- ColorizeStable
- DDColor Natural
- DDColor Artistic
Added a dedicated DDColor ONNX adapter that preserves the original luminance while predicting color channels.
Brightness and gamma
Added full-image tone correction:
- Brightness from -100 to 100
- Gamma from 0.20 to 3.00
- Default brightness: 0
- Default gamma: 1.00
- Settings are saved in config.json
- Correction is applied before the final upscaler
Smart face masking
Added optional smart occlusion and boundary protection using:
- occluder.onnx
- faceparser_resnet34.onnx
- XSeg_model.onnx
This is intended to preserve:
- Hair crossing the face
- Glasses
- Hats
- Foreground objects
- Face boundaries
Local prompt editing
Added local NVIDIA prompt editing using Diffusers and InstructPix2Pix:
- Enable/disable prompt editing
- Edit prompt field
- Negative prompt field
- Adjustable inference steps
- Optional processing of video frames
- CUDA/NVIDIA availability checks
- FP16 inference
- Attention and VAE slicing for lower VRAM use
- Automatic prompt-model caching during the session
- Resizes prompt-processing images and restores their original dimensions
ONNX compatibility and error handling
- Added automatic ONNX input-datatype detection
- Supports models expecting:
  - FP16
  - FP32
  - FP64/double
- Fixed the tensor(float), expected tensor(double) error
- Added handling for auxiliary ONNX inputs
- Added detection for invalid, non-finite model output
- Added detection for all-black model output
- Skips a failed enhancement model instead of producing black squares or terminating the entire batch
- Added automatic GPU-to-CPU fallback when a model cannot load with the selected provider
- Added clearer model download and compatibility errors
- Models download only when their associated feature is selected
Processing-chain improvements
The current image-processing order is approximately:
1. Detect target faces
2. Match indexed source identities
3. Swap faces
4. Apply smart occlusion protection
5. Apply face restoration
6. Apply colorization
7. Apply local prompt editing
8. Apply brightness and gamma
9. Apply final upscaling
10. Save the result
Saved settings
The following new selections are persisted in config.json:
- Face-restoration model
- Restoration strength
- Colorization model
- Upscale model
- Upscale factor
- Brightness
- Gamma
- Smart masking
- Prompt editing
- Positive prompt
- Negative prompt
- Prompt steps
- Video prompt-processing option

Install:
Extract the complete AI Generator folder.
Install 64-bit Python 3.11.
Run Setup.bat once.
Run Install_NVIDIA_Prompt.bat only if prompt editing is wanted.
Use Run.bat to launch program.
Prerequisites
-Python 3.11

Support
Paypal
https://www.paypal.com/paypalme/GameModNation
Patreon
https://www.patreon.com/c/3dmodelserver
Join the Discord
https://discord.com/invite/sMZuNzhmxC

