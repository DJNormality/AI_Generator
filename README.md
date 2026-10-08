# AI Generator

AI Generator is a Windows desktop application for batch face replacement, image and video processing, face restoration, colorization, upscaling, prompt-guided image editing, cropping, batch file renaming, and exploratory 3D mesh scanning.

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

### Standalone Colorize tab

- Colorize complete folders of black-and-white images without indexing source
  faces and without performing a face swap.
- Select independent input and output folders.
- Choose DDColor Natural, DDColor Artistic, or ColorizeStable.
- DDColor Natural is the recommended default for photographs because it keeps
  the original full-resolution luminance and predicts new color channels.
- Preserve every original filename.
- Preserve the alpha channel of transparent PNG images.
- Skip existing outputs or enable overwrite mode.
- Download the selected ONNX model automatically when it is missing.
- Display per-image and overall progress using the main green progress bars.
- Stop an active standalone colorization batch with the main Stop button.

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
- The rectangle is red while it is being drawn or scaled and turns green when
  the final crop selection is valid.
- Save the selected area as a new file.
- Preserves PNG transparency.

### Batch crop

- Crop an entire directory of images and videos.
- Choose common aspect ratios.
- Enter an exact output width and height.
- Keep the original centered crop behavior or choose **Custom selection**.
- Load the first image in the folder, or the first frame of the first video
  when the folder contains no images, and draw a reusable crop template.
- The template rectangle is red while being drawn and turns green after the
  final selection is completed.
- Apply the selected relative position to every image and video in the folder,
  even when media dimensions differ.
- Preserve video audio when producing the cropped video.
- Control whether existing output files are overwritten.

## Batch Renamer

- Rename images, videos, or all supported files.
- Find and replace text in filenames.
- Add prefixes and suffixes.
- Add sequential numbers with selectable starting value and digit count.
- Optionally include subfolders.
- Preview every old and new filename before applying changes.
- Uses temporary names internally to avoid collisions.

## Models

The **Models** section contains the raw binary Model Tool directly in its
main tab. It does not create a separate always-on-top window. Its file picker
uses **All files**, so a file does not need a recognized model extension.

The current interface embeds the complete 3D scanner directly inside the
**Models** tab. Texture Search, File Extractor, Music Studio, Audio Split,
and Video Editor are likewise mounted directly in their tabs; launcher pages,
extra tool windows, and embedded Back to Home buttons are no longer required.

- Scan raw bytes for ranked position-buffer candidates.
- Choose console-aware presets for PS1, PS2, PS3, PS4, PS5, Wii,
  GameCube, Xbox, Xbox 360, Xbox One, and Dreamcast. Presets select the usual
  byte order, alignment, and preferred numeric formats for that platform.
- Automatically recognize Wii `SRWiiDisplayList` and PS2
  `NiPS2GeometryStreamer` blocks in Gamebryo NIF files.
- Switch the independent search option between **Geometry** and
  **Animation / Rigging**.
- A cleaner settings notebook separates **Mesh**, **UV**, **Animation**, and
  **Texture** controls while keeping the compact results list and viewport
  visible. Selecting Animation / Rigging automatically opens its settings tab.
- Load an optional second **Animation / Skeleton File** using the unrestricted
  **All files (`*.*`)** picker. DAT, BIN, ANM, ANIM, SKEL, console-specific,
  extensionless, and other file types are accepted and scanned as raw bytes.
- Search animation and skeleton data for Float32/Float16 4x4 matrices, 3x4
  matrices, TRS transforms, common strides, both byte orders, and assumed bone
  hierarchy sequences.
- Merge a selected rig candidate over the current mesh preview. Bones are
  bright red, joints are numbered, and X/Y/Z axes are labeled at bone points.
- Use **Deep Rescan** to test two-byte stride increments and finely aligned
  offsets around the currently selected candidate.
- Stop normal or deep scanning at any time with **Stop Scan**. Partial results
  already found are preserved and ranked instead of being discarded.
- View live scan progress with a green percentage bar and a **Found items**
  counter during normal and deep scans.
- Candidate descriptions use compact numbered labels showing **Item number**,
  hexadecimal **Offset**, assumed **Size** using B/KB/MB/GB, vertex count,
  stride, numeric type, byte order, and confidence percentage.
- Test Float32, Float16, signed and unsigned 32-bit, 16-bit, and 8-bit values,
  including normalized short and byte formats.
- Test common vertex strides and padding values.
- Enter or correct vertex offset, count, stride, position type, UV offset, and
  UV type manually.
- Displays a white landscape grid on the XY ground plane with **Z Up**, including
  a white vertical Z-axis marker. The grid remains visible before a model loads.
- Read UInt16 or UInt32 face/index buffers as triangle lists or triangle strips.
- Preview candidate geometry in the built-in software 3D viewer.
- Scroll the ranked-candidate list with either the mouse wheel or its vertical
  scrollbar. Use the horizontal scrollbar for longer item descriptions.
- Hold **Ctrl** and use the mouse wheel to zoom.
- Hold **Alt** and drag with the left mouse button to rotate.
- Export a working candidate as Wavefront OBJ.
- Export the current result as an Autodesk-compatible ASCII FBX. The scanner
  still creates a valid empty FBX container when no vertices or faces were
  found. Recovered bones are included in the FBX hierarchy when available;
  skin weights cannot be created unless weight data is also recovered.

The scanner is heuristic. It cannot automatically decode every proprietary,
compressed, encrypted, interleaved, or specially quantized format. Ranked
candidates are starting points for manual adjustment. A format-specific parser
can be added later when sample files and their expected geometry are available.
Console-specific Gamebryo render streams can contain display-list commands in
addition to raw attributes, so a dedicated stream decoder may still be needed
for perfect extraction from some games.

## Textures

AI Generator starts in an empty black top-level **Home** section. The existing
image and video tools are grouped under **Images**, while **3D Models** and
**Textures** remain separate neighboring sections. Each expanded tool runs
inside the same application window with a **Back to Home** button.

The embedded Textures tool:

- Opens any file extension and searches its raw bytes.
- Detects embedded PNG, JPEG, DDS, BMP, KTX, KTX2, and PVR signatures.
- Shows numbered results with format, byte offset, dimensions when available,
  and B/KB/MB/GB size.
- Displays scan progress and result count and supports stopping a scan.
- Previews formats supported by the installed Pillow codecs.
- Extracts one selected texture or every detected texture to a folder.
- Uses vertical and horizontal result-list scrollbars plus mouse-wheel scrolling.
- Adds a full **Raw Settings** decoder with width, height, decimal/hex data
  offset, row stride, texture count, per-texture stride, little/big endian,
  alpha mode, palette offset, palette type, and palette size controls.
- Supports RGBA/BGRA/ARGB/ABGR 8888, RGB/BGR 888, RGB/BGR 565, RGBA5551,
  ARGB1555, RGBA/ARGB4444, L8, A8, LA88, 4-bit and 8-bit indexed palettes,
  DXT1/BC1, DXT3/BC2, DXT5/BC3, ATI1/BC4, and ATI2/BC5.
- Provides Linear, Morton/Z-order, 4x4, 8x8, 16x16, PS2 GS, Wii/CMPR,
  GameCube, and experimental Xbox 360 swizzle/tiling selections. Console game
  formats can still use custom layouts, so these presets are best-effort.
- Adds explicit platform choices for PC Linear/Direct3D and Morton layouts,
  Switch Tegra block-linear/GOB, PS1 linear and twiddled, PS2 GS PSMCT32/PSMT8/
  PSMT4, PS3 RSX linear/swizzled, PS4 GNM micro/macro tiled, and PS5 GNMX
  tiled textures. A selectable tile/GOB block height helps tune platform data.
  Switch, PS4, and PS5 presets are marked experimental because the exact layout
  also depends on mip level, GPU surface mode, pitch, and game engine metadata.
- Decompresses None/Auto, ZLIB, raw DEFLATE, GZIP, BZIP2, LZMA/XZ, two common
  LZSS 12/4 flag orders, LZ4 frame/block, Zstandard, Brotli, Snappy, LZO,
  PackBits RLE, byte-pair RLE, Nintendo LZ10/LZ11, and Nintendo Yaz0 data for
  preview and decompressed export without changing the source file.
- LZ4, Zstandard, Brotli, Snappy, and LZO use optional Python packages. When a
  package is missing, the GUI displays the exact install command or requirement.
  Decompressed output has a 1 GB safety limit.
- Also supports LZF plus extracting the first payload from ZIP and 7-Zip
  containers. LZF and 7-Zip use the optional `python-lzf` and `py7zr` packages.
- The preview supports mouse-wheel zoom, left-button panning, Fit, and 100%.
- Exports the current decoded texture as PNG, JPG, DDS, or TGA. **Export All**
  converts all detected textures to PNG; **Export All Raw Textures** processes
  configurable texture arrays into the selected PNG/JPG/DDS/TGA format.
- **Stop Scan** interrupts automatic scanning or a long batch export while
  preserving results and files already completed.

## Files

The top-level **Files** section opens a built-in decompressor and extractor. It
does not require QuickBMS or external scripts and does not attempt password
cracking or encryption bypass.

- Opens every file extension as raw bytes.
- Indexes recognizable headers, hexadecimal offsets, buffer sizes, stored
  filenames, and little- or big-endian offset tables.
- Extracts structured ZIP and TAR hierarchies and preserves stored subfolders.
- Detects and attempts standard ZIP, TAR, GZIP, BZIP2, XZ/LZMA, ZLIB, and
  DEFLATE-style streams supported by Python's installed decoders.
- Recursively scans successfully decompressed buffers for nested files and
  additional compressed streams.
- Uses nearby filename tables when available; otherwise names buffers using
  their offsets.
- Displays results in a collapsible hierarchy with **Expand All** and
  **Collapse All** controls.
- Keeps the displayed identification results limited to the initial local
  scan. The scanner does not automatically browse the web or merge online
  guesses into the result list.
- Adds an optional **Search Online** button for the selected result. It opens a
  browser search using only the local filename/extension, detected header or
  type, status, and suggested algorithm/tool. File contents are not uploaded,
  and the online search does not alter the local scan results.
- Extracts one buffer or reconstructs all detected folders and files.
- Includes an embedded **Cutter** that accepts automatic, hexadecimal, or
  decimal start offsets. Its optional end offset defaults to the end of the
  input file, and the interface displays start, end, exact byte size, and the
  detected file type before export.
- Cutter exports accept a custom filename and selectable extension. When the
  name is blank, a source-name plus hexadecimal-offset filename is generated;
  existing files receive numbered suffixes instead of being overwritten.
- Cutter type detection checks the bytes at the requested offset and
  automatically selects known PNG, JPEG, DDS, BMP, GIF, WAV, AVI, OGG, ZIP,
  compressed-stream, archive, executable, and related extensions.
- Labels positively identified encrypted entries as **ENCRYPTED** and skips
  decryption. Unknown high-entropy data is described as compressed or
  encrypted rather than being guessed or cracked.
- Adds a **Suggested Method / Tool** column. Recognized OpenSSL, PGP, encrypted
  ZIP, 7z, RAR, and PDF data receive appropriate tool/key guidance. Embedded
  strings are checked for hints such as AES, XTEA, XXTEA, Blowfish, ChaCha,
  Salsa20, DES/3DES, and RSA.
- For unknown proprietary formats, suggests looking for matching format
  documentation or a QuickBMS `.bms` script using the game and archive name.
  This is identification guidance only: no passwords, keys, or encryption are
  brute-forced or bypassed.

## Interface Improvements

## Music Editor

- Adds dedicated **Drums**, **Bass**, **Turntable**, and **Vocals** subtabs.
- Drums provides an eight-lane step sequencer; Bass provides a low-register
  twelve-note sequencer. Both can loop, export WAV/MP3/MIDI, and save patterns
  into any of the ten Song mixer channels.
- Turntable exposes the loaded track's speed and gain controls with WAV/MP3
  mix export. Vocals embeds vocal/instrumental stem separation and optional
  merged-stem output directly inside Music.

The top-level **Music** section opens an embedded audio editor.

- Opens MP3, WAV, FLAC, M4A, AAC, OGG, WMA, and other FFmpeg-supported audio.
- Displays a compact waveform and file duration, sample rate, channels, and bit depth.
- Trims by start/end time, changes playback speed and pitch together, adjusts volume in dB,
  converts mono/stereo or selects a channel, and applies fade-in/fade-out.
- Exports edited audio as WAV or MP3 with selectable MP3 bitrate.
- Provides fast center-channel vocal cancellation and optional Demucs AI separation into
  `vocals.wav` and `instrumental.wav`.
- Transcribes detected musical pitches to MIDI. The built-in NumPy melody detector works
  without Basic Pitch and writes a standard MIDI file directly; optional Basic Pitch AI
  provides a higher-quality alternative when it supports the installed Python version.
  MIDI is note transcription rather than an audio container, so dense mixes may need cleanup.
- Long Demucs, MIDI, and export operations include a Stop button.
- Includes an interactive two-octave piano-roll lesson view. Choose a root,
  scale, chord, and octave to display the matching notes. White and black piano
  keys turn orange when clicked, display the played note, and sound through
  Windows when `winsound` is available.
- Adds a **Guitar & Chords** lesson tab with a six-string standard-tuning
  fretboard. Click any string/fret to hear its note, or hold the left mouse
  button and drag across strings to strum the selected chord in real time.
- Includes all 12 roots and 30 common chord qualities—360 generated chord
  selections—including major/minor, power, diminished, augmented, suspended,
  sixth, seventh, ninth, eleventh, thirteenth, altered dominant, and add chords.
  The fretboard displays the chord notes, generated fret positions, orange
  active strings, plus Play Chord and up/down strum controls.
- Piano and guitar include compact horizontal step sequencers with no embedded
  scrollbars. The Piano section adds a dedicated falling-note playback window
  inspired by modern piano visualizers and a compact three-octave keyboard.
- Each sequencer has independent volume and left/right panning plus customizable
  note, background, measure-column, and bar/grid colors.
- Piano and guitar patterns export from their own sections as WAV, MP3, or a
  standard `.midi` note sequence. WAV/MIDI are generated directly; MP3 uses
  Pydub and FFmpeg.
- Guitar customization includes Standard, Drop D, half/whole-step down, DADGAD,
  Open G, and Open D tunings; capo positions 0–12; and separate color pickers
  for the wood fretboard, strings, metal frets, and fret dots.
- Piano and guitar sequencers support 1–9,999 bars with horizontal scrolling.
  Patterns can be saved into any of ten mixer channels.
- The **Song** window places saved channel patterns on a multichannel timeline.
  Blocks can be snapped by sixteenth, quarter, or bar; freely positioned;
  dragged between channels; right-click removed; played; and mixed to WAV/MP3.
- Demucs splitting saves vocals and instrumental as individual WAV files, with
  an option to reconstruct and save `merged_stems.wav` in the same folder.
- Audio separation now opens as its own **Audio Split** tool instead of being
  mixed into the custom Song Studio. It offers a source file, output folder,
  Demucs model choice, Stop control, individual vocal/instrumental outputs,
  and optional merged-stem export.
- Song Studio now locates `tools\\ffmpeg\\bin` directly in code, so opening
  MP3/M4A/AAC files works even when `main.py` was launched without `Run.bat`.

## Video Editor

The top-level **Videos** section opens a dark embedded non-destructive editor.

- Add multiple MP4, MOV, MKV, AVI, WebM, or M4V clips to a visual timeline.
- Drag clips with frame, 0.1-second, 0.5-second, one-second, or free movement;
  enter an exact custom timeline position; cut a selected clip at an exact time;
  remove clips; or clear the project.
- Crop, scale, rotate, zoom, change speed, and apply video fade-in/fade-out.
- Adjust brightness, contrast, saturation, and hue with grayscale, sepia,
  vintage, cool, warm, sharpen, and blur filters.
- Exports the processed timeline to H.264/AAC MP4 using FFmpeg and includes a
  Stop button. Every launch begins with empty clips and default settings.

## Home Visuals

- Uses the supplied blue binary artwork as a responsive cover background.
- Keeps the visible neon disc at 100% opacity, removes its exact-black rectangle
  with a shape mask, and Overlay-blends it into the Home wallpaper.
- Home is now background-only below the primary tabs. Image progress bars,
  status controls, and processing buttons are hidden there.
- Run `Install_Music_Tools.bat` from the main folder for complete audio setup.
  It installs Pydub, Python 3.13's `audioop-lts`, ImageIO-FFmpeg, downloads a
  private FFmpeg/FFprobe build into `tools\\ffmpeg\\bin`, installs Demucs when
  compatible, and verifies the finished installation. `Run.bat` automatically
  adds the private FFmpeg folder for AI Generator without changing system PATH.
- Basic Pitch is installed only on its supported Python versions (3.7-3.11).
  Python 3.13 installations continue to use the built-in MIDI detector.

## Online Library

- Adds an embedded **Library** tab with Tutorials, Instructions,
  Configurations, and Research views.
- Organizes searches by Games, Movies, Sports, TV, Stream, Music, Nature,
  Companies, Jobs, Crypto, Stocks, and Gas.
- Uses public Wikipedia and Google News results without requiring an API key.
- Checks internet access automatically. When offline it displays
  **Not Connected** at the bottom and disables online searching.
- Opens broader Google searches in the default browser, Microsoft Edge,
  Firefox, Safari, or every detected installed browser. Missing browsers are
  reported instead of being launched blindly.

## Asset Sorter

- Adds a dedicated **Sort** tab with directory selection and a complete move
  preview before filesystem changes begin.
- Creates Models, Textures, Animations, and Sounds folders while preserving
  every source subdirectory beneath its assigned category.
- Recognizes common model, animation, texture, and audio extensions. Unknown
  types always prompt for Models, Textures, Animations, Sounds, or Skip.
- For same-name `.fbx`, `.smd`, or `.cast` files, the largest is treated as the
  model and smaller matches receive `_anim_1`, `_anim_2`, etc. in Animations.
- Never overwrites a file. Every existing or planned collision receives a
  numbered filename, including an existing `Extracted.zip` archive.
- Builds `Extracted.zip` containing only the four organized category folders.

## Design Studio

- Adds a layered **Design** tab for blueprint drawing and UV-layout templates.
- Includes Select, Paint, Erase, Clone Stamp, Smudge, Blur, and Sharpen tools;
  raster filters operate on imported image layers.
- Blueprint shapes include square, triangle, circle, and oval tools with
  explicit width, height, scale, stroke, grid, and snapping controls.
- Information shows X/Y position, width, height, and calculated path distance.
- Electrical, plumbing, and water tools connect point-to-point; press Escape
  to finish the active run. Each finished run becomes a separate layer.
- Provides Blank, Room, House Grid, Cube UV Cross, Cylinder UV, and Sphere UV
  templates plus an expanded modern item catalog: doors and framing, garage
  doors, fireplaces, bathtubs, showers, steps, railings, windows, plumbing
  fixtures, appliances, furniture, lighting, bedding, and cabinetry.
- Adds a blueprint-style drawing information block with editable project
  title, drawing number, revision, sheet, scale, and author fields. Each block
  is an independent layer and is included in PNG exports.
- Adds a **UV Mapping** tool inside Design. Open an OBJ, ASCII FBX/model file,
  raw binary model, or image and choose **Scan & Generate** to create a flat UV
  layer. OBJ texture coordinates and face indices are reconstructed directly;
  ASCII FBX and generic aligned Float32 UV buffers have fallback scanners.
- UV layouts support **Wireframe**, **Solid**, and **Vertices** viewing modes
  and remain normal Design layers for visibility, ordering, coloring, project
  saving, and PNG export.
- Every inserted or drawn item is an independent layer with visibility,
  ordering, deletion, selection, movement, and individual color controls.
- The top Design header is collapsible. Projects save as `.aidesign` and the
  visible document can export to PNG.

## Research Workspace

- Adds a **Research** tab with a collapsible input-file header and paged hex/
  ASCII viewer.
- Finds hexadecimal byte sequences or ASCII, UTF-8, and UTF-16LE strings,
  clearing old results before every search and listing match counts and offsets.
- Double-clicking a match jumps the hex viewer to that exact offset.
- Detects common embedded PNG, JPEG, DDS, ZIP, WAV, OGG, PDF, GIF, BMP, KTX,
  GZIP, and 7-Zip signatures with candidate offsets and sizes.
- Includes Stop scan, Extract file, and Extract all controls. Output naming is
  collision-safe. Detected results automatically use their real extension:
  `.png`, `.jpg`, `.dds`, `.zip`, `.wav`, `.ogg`, `.pdf`, `.gif`, `.bmp`,
  `.ktx`, `.gz`, or `.7z`. For example, BMP results become `TEST.bmp`,
  `TEST_1.bmp`, and so on. The manual extension field is used only as a
  fallback for an unknown type.

## Sound Scanner

- Adds a dedicated **Sound** tab immediately after Textures.
- Scans arbitrary binary files and banks for documented WAV/WEM, AIFF, Ogg,
  Opus, FLAC, MP3, AAC, MIDI, FSB4/FSB5, Wwise BNK, Sony VAG/PSF, CRI ADX,
  Nintendo BRSTM/BFSTM/BCSTM, Xbox XMA, XM, S3M, and IT signatures.
- Shows assumed format, offset, size, and the output structure for every match.
- Opens ZIP-compatible packages and retains their internal folder and filename
  structure when extracting sound assets.
- Includes Stop scan, Extract selected, and Extract all controls. Existing
  files are never overwritten; numbered suffixes are added automatically.

## PS2 Extract Workspace

- Adds an embedded **Extract** main tab with Archives, Models, Textures,
  Animations, and Batch Processing sections.
- Includes PS2 Generic, Wild Arms 3, Wild Arms Alter Code: F, and Auto Detect
  profiles so game-specific rules can be refined without changing the GUI.
- Archives can scan BIN files for embedded headers and plausible little-endian
  offset tables. The LZSS action implements the common PS2/Okumura 4 KB ring
  buffer variant with LSB-first flags, 12-bit distance, and 4-bit length.
- LZSS output is bounded and validated to prevent a wrong profile from causing
  runaway memory use or writing an implausible expansion.
- Detects PS2-oriented TIM2 textures, VAG/Sony sound banks, Gamebryo NIF and
  RenderWare model markers, MOT/ANM animation markers, plus common embedded
  image/audio/archive signatures.
- Model, Texture, and Animation sections filter results for their asset type.
  Extract Selected and Extract All never overwrite existing output files.
- Batch Processing accepts a directory, preserves its relative structure,
  optionally tries LZSS decompression, shows per-file progress, and can be
  stopped safely. Source game files are always read-only.
- Wild Arms-specific archive tables, mesh conversion, texture decoding, and
  skeletal animation conversion are framework hooks until verified against
  representative game files and the known Wild Arms utilities.

## Animated interface

- Main navigation uses precision-rounded buttons in this order: Home, 3D
  Models, Textures, Sound, Files, Music, Videos, Design, Sort, and Research.
- The animated cyber background is restricted to **Home** so tool tables and
  text fields stay readable. Blue Matrix-style data flows downward while a
  soft blue fog layer rolls across the original cyber artwork.
- The Multiply-blended disc appears only on Home. Its redraw interval is halved
  to 14 ms for a true 100% increase over the prior speed. Home also contains
  icon-only Patreon, Discord, PayPal, and Website
  shortcuts. The Website globe opens the 3D Model Archives site.
- **Midi** is a dedicated subtab inside the Music studio.

## Building the Windows EXE

1. Install AI Generator normally with `Setup.bat` and confirm `Run.bat` works.
2. Place `Build_EXE.bat`, `AI_Generator.spec`, and `main.py` together in the
   main AI Generator directory.
3. Double-click `Build_EXE.bat`. It uses `Scripts\python.exe` first, then a
   `.venv` or installed Python 3.13 only when necessary.
4. The builder verifies NumPy, SciPy, scikit-learn, scikit-image, and
   InsightFace before PyInstaller starts. If SciPy has broken or mismatched
   extension modules, compatible precompiled Python 3.13 wheels are
   automatically reinstalled. The build stops instead of creating an
   incomplete EXE if InsightFace still cannot import.
5. The builder installs PyInstaller without upgrading Torch, then creates a
   no-console one-folder application.
6. Launch `dist\AI_Generator\AI Generator.exe`. A distributable
   `AI_Generator_Windows_EXE.zip` is also created beside the build script.

The one-folder format is intentional: ONNX Runtime, InsightFace, Torch,
Diffusers, CUDA providers, FFmpeg, models, and dynamically loaded plugins are
more reliable this way than in a single compressed executable. Existing
`models` and `tools` folders are copied into the finished application, while
personal `config.json`, API keys, indexed faces, and temporary files are not
added automatically.
- Requires `pydub` and FFmpeg for general audio. Optional features use `demucs` and
  `basic-pitch`; missing packages produce an exact installation message in the GUI.

- Application renamed to **AI Generator**.
- Modern dark tabbed interface with separate top-level **Home**, **Images**,
  **3D Models**, **Textures**, **Files**, **Music**, and **Videos** sections.
- Global dark ttk styling now applies to every embedded tool, including its
  frames, labels, buttons, entries, combo boxes, notebooks, trees, and panes.
- Wider landscape layout keeps the image and video tools in one horizontal
  tab row and reduces unnecessary vertical space.
- Responsive weighted layout keeps progress bars and bottom action buttons
  visible when the window is resized smaller. The center notebook absorbs the
  size change instead of pushing controls below the screen.
- Home tool tabs have vertical scrollbars and mouse-wheel scrolling, so longer
  Prompt Edit, Crop, and Rename controls remain reachable in short windows.
- Image processing progress bars and Run/Review/Clear/Stop controls are now
  visible only inside the **Images** section and no longer appear beneath the
  Home, Models, Textures, Files, Music, Videos, or Library sections.
- Reduced minimum window size and compact bottom-button widths support smaller
  desktop layouts without clipping the GUI.
- Startup is centered at approximately 1120×700 with a 900×620 minimum.
- The Rename utility now lives under **Files → Rename**, not Images.
- The Models viewport adds Solid, Wireframe, Solid + outline, and Points modes,
  customizable background/surface/outline/vertex colors, line width, and point size.
- Texture scan results are validated by decoding them first. False detections
  are hidden and verified images appear in a thumbnail filmstrip/gallery.
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
| `model_scanner.py` | Raw mesh scanner, 3D preview, and OBJ exporter |
| `texture_scanner.py` | Embedded texture signature scanner, preview, and extractor |
| `file_scanner.py` | Built-in archive, compression, header, offset-table, and buffer extractor |

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

### Standalone colorization fails

- Start with DDColor Natural, which is recommended for complete photographs.
- Confirm the input folder contains PNG, JPG, JPEG, WebP, BMP, TIF, or TIFF images.
- Confirm the output folder is writable and has enough free disk space.
- Delete a partially downloaded colorizer ONNX file and run the Colorize tab
  again so AI Generator can download a clean copy.
- Try CPUExecutionProvider if a GPU provider returns invalid or black output.

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
