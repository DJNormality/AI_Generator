<img width="1122" height="732" alt="python_OcwNpU430D" src="https://github.com/user-attachments/assets/3855bce6-eda4-41e2-9eb9-cc7483e33f62" />

AI GENERATOR - FEATURE LIST
Compiled November 26, 2026
Windows project coverage: updates through V329
Android Food companion coverage: 1.0.328

This inventory combines the available application source, supplied tool modules,
and completed updates in this project. Exact availability depends on the installed
version, downloaded models, supplied plug-ins and external programs. Android Food
is a separate companion application, not the entire Windows suite on Android.

CONTENTS
01. Home, navigation and general interface
02. Processing, settings and installation
03. Photos and face processing
04. Image editing, icons and enhancement
05. Models, 3D creation and rigging
06. Textures and UV tools
07. Files and batch utilities
08. Research, Library and engine/game references
09. Extract and asset inspection
10. Engine workspaces
11. Games, Arcade and console navigation
12. Capture and porting
13. Music Player and AI music creation
14. Splitter
15. Vocalist
16. Autotuner
17. Music Info, metadata and playback effects
18. Chords and LearnOn
19. Studio and instruments
20. Video
21. Design and layout editing
22. Cabinet Builder
23. Sprite Skinner
24. DYI project assistant
25. JuiceWRLD media library
26. Food - Recipe Maker
27. Food - Meal Maker and timer
28. Food - ingredient cost estimates
29. Food for Android
30. Integration and offline-use notes


01. HOME, NAVIGATION AND GENERAL INTERFACE
-----------------------------------------
- Home launcher with visual page icons.
- Configurable icon images, labels, visibility and sizing.
- Icon positioning, ordering, sorting and grid/snap organization.
- Saved launcher preferences and icon arrangements.
- Animated Home background with moving fog and star/twinkle effects.
- Main-page and subtool navigation through icon toolbars.
- Compact Vista-style controls and transparent icon artwork.
- Custom toolbar icons and built-in icon selection.
- Built-in icon libraries with category filtering and search.
- Paginated icon browsing and previous/next navigation.
- Icon-only choices in the updated built-in icon dialog.
- Toolbar ordering and hold/drag interactions in supported toolbars.
- Home and settings controls available from the shared interface.
- Session Tool Explorer for revisiting open workspaces.
- Route history with back/forward navigation.
- Tool close, reopen and close-all actions.
- Live tool instances retained during supported navigation changes.
- Shared playback controls and visual feedback in the main interface.
- Window minimize, maximize, restore and fullscreen controls.
- Supported per-workspace layout and position preferences.
- Searchable/filterable lists and tree views throughout the suite.
- Sortable table headings and contextual sorting options.
- Scrollable content regions with click-armed mouse-wheel routing.
- Task status, progress and error feedback.
- Filling percentage bars in updated processing tools.
- Compact icon buttons with tooltip descriptions in supported tools.
- Support/community links in the application interface.
- Version display and versioned incremental updates.
- Food first-open activation fix: Recipe Maker is initialized after the page
  is visible and its layout is ready, without first opening another Food tool.


02. PROCESSING, SETTINGS AND INSTALLATION
---------------------------------------
- Source, target, output and temporary directory selection.
- Background workers for supported long-running operations.
- Start/stop/cancel controls where the underlying task supports cancellation.
- Current-task and overall progress tracking in the image pipeline.
- Saved application settings and per-tool configuration.
- Resume/checkpoint handling for supported batch operations.
- Reprocessing and output-reuse options in the face/image workflow.
- CPU, CUDA and DirectML provider selection in compatible image tools.
- Auto/GPU/CPU selection in the updated Vocalist workflow.
- Local-model setup helpers for supported AI features.
- External-tool executable paths and dependency setup controls.
- Versioned Rebuild.bat update packages.
- Automatic target-directory handling in recent Windows update packages.
- Preflight syntax checks, backups and rollback in recent incremental installers.
- Original-environment/path repair utilities.
- Standalone launch helpers for supported tools, including Music and Cabinet
  Builder project variants.
- Optional executable-build batch workflows supplied during the project.


03. PHOTOS AND FACE PROCESSING
-----------------------------
- Face Swap workspace with selectable swapper models.
- Source-image and target-media processing workflow.
- Face indexing and index rebuild controls.
- Face-consistency settings.
- Original and reduced processing-resolution choices.
- Blend percentage and edge-feather controls.
- Face color-correction option.
- Quick-scan option.
- Review pass and manual-review modes.
- Existing-output reprocessing controls.
- Smart masking and face-boundary/occlusion protection.
- Combined use of compatible occluder, face-parser and XSeg models.
- Face-restoration model selection, including configured CodeFormer, GFPGAN,
  RestoreFormer++ and GPEN choices when their model files are installed.
- Restoration-strength adjustment.
- Batch image processing with output and temporary-file management.
- Video reconstruction from processed temporary frames.
- Standalone image colorization workflow.
- Colorization choices such as ColorizeStable and DDColor variants when available.
- Prompt-based image editing through configured local or external engines.
- Qwen/prompt-edit workspace and local-model options.
- Prompt, strength and model configuration for compatible image-edit backends.
- Brightness and gamma adjustments.
- Image upscaling through configured RealESRGAN, UltraSharp and UltraMix models.
- Upscale-factor selection, including 2x/4x options.
- Manual image cropping.
- Guide crop and sprite-sheet/image slicing.
- Batch cropping by aspect ratio or exact dimensions.
- Common portrait, square and landscape aspect-ratio presets.
- Centered or custom crop placement.


04. IMAGE EDITING, ICONS AND ENHANCEMENT
--------------------------------------
- Embedded Image Editor.
- Layer controls and visibility.
- Brush tools and selectable brush tips.
- Drawing and shape controls, including filled shapes.
- Color picker and HEX color entry.
- Font selection for text-related editing.
- Attribute editing and application to selected content.
- Fit-to-window viewing and zoom-related controls.
- Icon Maker workspace for creating/editing icon artwork.
- Color and shape tools in Icon Maker.
- Classic image-enhancement workspace.
- Node-graph enhancement workspace.
- Selection of compatible ONNX enhancement models.
- Denoising controls, including median denoise.
- Export/background-color handling for formats without transparency.
- PNG export and alpha-aware image workflows in compatible editors.


05. MODELS, 3D CREATION AND RIGGING
---------------------------------
Models / Scan
- Open and inspect supported model/binary files.
- Generic binary mesh scanning.
- Mesh candidate identification and preview.
- Integrated 3D preview and view transforms.
- Combined Scan & Options, View & Transform and Batch Export workspace.
- Scale, rotation and position controls.
- Apply current preview transforms to supported exports.
- Queued/batch export operations.

Models / Create
- Add reference images, image folders or video inputs.
- Index reference images.
- Build and rebuild generated/reconstructed meshes.
- Local AI 3D setup options, including the configured SF3D integration.
- Depth-model and COLMAP configuration for supported reconstruction paths.
- Export generated meshes as OBJ or GLB.

Design / 3D
- Polygon/model editing workspace.
- Object selection and transformation.
- Move, scale and rotation workflows.
- Position, size and related object attributes.
- Vertex-oriented editing controls.
- Extrude, cut, connect and split operations in the editor.
- Boolean-operation controls.
- Primitive/object creation, including cube-based construction.
- Duplicate and delete actions.
- Undo/redo checkpoints.
- Import, open, save and export actions for supported mesh/project formats.
- Projection selection and saved views.
- Optional four-view display.
- World-axis, axis-lock and grid controls.
- Wireframe/solid display modes.
- Lighting controls and light editing.
- Material creation, selection, editing and application.
- Material drag/drop interactions.
- UV-related editing controls.
- CPU/resource feedback in the 3D workspace where available.

Auto Rig
- Open a mesh or use a selected mesh from the 3D workspace.
- Local Blender-based rigging workflow.
- Biped template and editable joint landmarks.
- Normalized width/depth/height joint placement.
- Reset joint-template controls.
- Reference-image upload and preview.
- Automatic rig and skin-weight generation for compatible inputs.
- Configurable Blender path, output directory and export options.
- Skeleton preview.
- Background execution, stop controls and job/status feedback.
- Open the generated result/output folder.
- Optional configured cloud-provider adapters; these are separate from local rigging.

3DSim
- Integrated mesh view and transform workspace.
- Wireframe preview.
- Scale, position and rotation application.
- Optional supplied 3DSimED integration for proprietary formats.


06. TEXTURES AND UV TOOLS
------------------------
Texture Scan
- Automatic texture candidate scanning inside supported files.
- Configurable raw-texture dimensions, formats and decode settings.
- Candidate tuning and search limits.
- Detected-texture list and preview.
- Open DDS/PVR textures and compatible arbitrary binary inputs.
- Compression analysis and candidate testing.
- Decode/preview candidate textures.
- Use a detected candidate as raw data.
- Extract original texture data.
- Export individual/all detected textures.
- Export raw-texture results.
- Index supplied QuickBMS/Noesis script collections.
- Add script folders or ZIP collections.
- Stop scanning and return-to-Home navigation.

RGB Mixer
- Single-image RGB channel mixing.
- Live color preview.
- Image and mask import.
- Alpha-mask handling.
- Mask inversion and removal.
- Color reset and PNG export.

UV Layout
- UV-layout workspace for compatible meshes.
- UV inspection and layout editing/export paths provided by the installed tool.
- Related UV mapping controls in Design's layout/3D editors.


07. FILES AND BATCH UTILITIES
----------------------------
Convert
- Script-driven batch file conversion.
- Scan an input directory and discover supported candidates.
- Include subfolders.
- Preserve folder structure when converting.
- Optional overwrite behavior.
- Reload conversion scripts.
- Load a supplied Python script archive.
- Optional Blender/3DS Max host-runner integrations for compatible scripts.
- Background conversion and stop controls.

Rename
- Batch file-renaming workflow.
- Input/output naming configuration and preview-oriented processing.
- Apply renaming to supported file selections/directories.

Sort
- Preview file sorting before applying changes.
- Asset organization based on supported naming/type rules.
- Collision-aware sorting behavior.
- Move files and create ZIP output.
- Continue supported interrupted sorting operations.

Remove
- Separate file and folder cleanup views.
- Directory scanning and filtering.
- Select-all and selected-item removal controls.
- Review selected results before applying cleanup actions.

Cutter / File Scanner
- Scan data structures, buffers and embedded-file candidates.
- View detected entries in a hierarchical list.
- Expand/collapse entry trees.
- Read data from a chosen offset.
- Export a selected byte range/cut.
- Extract selected entries or all supported entries.
- Rebuild supported directory structures during extraction.
- Search-online action for research assistance.

Compress
- Directory/file ZIP workflows.
- Automatic ZIP creation after the configured short delay.
- Output selection and batch-oriented archive creation.


08. RESEARCH, LIBRARY AND ENGINE/GAME REFERENCES
----------------------------------------------
- Binary Research workspace.
- Hex inspection.
- String finding and search results.
- Signature and embedded-file discovery.
- Offset/page navigation through inspected data.
- Extract a detected file or all detected files.
- Stop long-running scans.
- Online reference Library search.
- Web search and open-selected-reference controls.
- Connection checking for online Library services.
- Offline engine/game reference catalogue.
- Optional game examples in catalogue results.
- Engine and game source links.
- Catalogue refresh/update, clear and CSV export controls.
- Supplied schema/definition collections used by compatible extraction tools.


09. EXTRACT AND ASSET INSPECTION
-------------------------------
- PS1/PS2-oriented asset extraction framework.
- Native PC asset scanning in supported readers.
- Legacy-format reader/converter controls.
- Supported archive/container inspection.
- File and optional index-file input.
- Output-directory selection.
- Selected or batch extraction.
- LZSS decompression attempts for supported data.
- Rescan decompressed data for recognizable PS2 assets.
- Raw sound-bank scanning and extraction.
- Sound scan/playback and conversion actions.
- Structure-preserving output where supported.
- Lightweight 3D and animation-validation preview.
- Skeleton import and animation append actions in compatible preview workflows.
- NIF workspace with block and texture inspection.
- Reader/converter discovery and selection.
- Compatibility workspace for native readers, verified CLI commands and external UIs.
- Imported script/schema catalogues for supported formats.
- Error/status reporting when a format or supplied dependency is unsupported.


10. ENGINE WORKSPACES
---------------------
Common engine interface
- Dedicated engine pages with archive/assets views and auxiliary SDK/tool tabs.
- Standardized preview, output and external-helper configuration patterns.
- Batch operations where the specific engine reader provides them.

Havok
- Conversion and header inspection.
- Havok string discovery.
- Current-input preview.
- Recursive folder conversion.
- Source preservation and overwrite options.
- Automatic tool discovery and saved tool paths.
- TagTools install/update integration.
- Blender/Noesis add-on folder access.
- Supplied skeleton/conversion options.

Anvil / Forge
- Supported Forge archive browsing and extraction.
- Archive-entry and asset views.
- Model/asset preview and view reset.
- Optional Oodle DLL selection for compatible compressed content.

Unity
- Dedicated Unity asset-processing workspace and configured helper integrations.

Unreal
- Dedicated Unreal asset-processing workspace and configured helper integrations.

Creation
- BSA/BA2 archive browser.
- NIF-oriented inspection and preview workspace.

NeoX
- Native extraction and shared model/texture preview.
- ZZZ4 block scanning and supported model conversion.

Blackspace
- Extraction/conversion workspace.
- XML decryption controls.
- Supported batch conversion.

Insomniac
- Layout CSV input and extraction workflows.
- Shared model/texture viewport.
- Block decoding and saved decoded output.
- Imported schema database.
- IGZ conversion/status controls.
- Supplied converter GUI, endian and texture-related helpers.
- Supported FBX/batch-conversion paths through configured tools.

Disrupt
- Supported extraction and asset preview.
- Hash-name loading and game-file lists.
- Imported file-list support.
- Project XML/list handling.
- Binary metadata XML export.
- Gibbed object-definition/schema integration.

Frostbite
- Engine workspace and supplied Frosty-helper integration.
- Profile and build lists.
- Import/select compatible keys.
- Import and apply supported cache data.
- Refresh and helper-path configuration.

Decima
- Supported native archive and asset inspection.
- Selected or batch extraction.
- Asset-path browsing.
- Localization export and language controls.
- Supplied Workshop CLI integration.
- Preview, output-folder and stop controls.


11. GAMES, ARCADE AND CONSOLE NAVIGATION
---------------------------------------
- Games/Arcade launcher with console and game filters.
- Saved custom game/console icon images and positions.
- Cover-image upload, removal and optional online cover search.
- Game-to-console memberships and filtering.
- Configured file/application launch actions.
- Console-oriented workspace/launcher entries for the project's configured
  PlayStation generations, Game Boy Advance, GameCube, Wii, Xbox 360 and
  Windows/PC categories; Switch integration is also part of the project setup.
- Per-console emulator/tool setup and launch configuration where installed.
- Package/tool workflows for the supplied PS4/PS5-related utilities.
- RPCS3 integration/configuration for the supplied PS3 workflow.

Game workbenches
- Wild Arms 3 asset workflow.
- Wild Arms Alter Code F asset workflow.
- Twisted Metal series workspaces, including original PlayStation titles,
  Small Brawl, Head On, Harbor City, Black and the 2012 game where supplied.
- NBA workbench using the supplied NBA exporter tools.
- Horizon assets and batch-conversion workflows.
- Horizon EDGE/TXT/SMD animation-conversion helper paths.
- GTAV workbench with CodeWalker-related tooling and native asset operations.
- GTAV RPF input, preview, XML editing/conversion and format/tool controls.
- GTAV selected-image export and DDS-to-PNG conversion.

Console names are launcher/workspace categories. They do not mean the application
itself implements a working emulator for every listed console. Some third-party
emulators and utilities open externally rather than remaining inside the main UI.


12. CAPTURE AND PORTING
----------------------
Capture
- Running-process selection and connection workflow.
- RenderDoc-related capture controls.
- Disconnect and saved capture/tool settings.
- Captured mesh conversion through configured tools.

Porting
- Fortnite Porting launcher.
- Official-release updater integration for the configured porting application.
- Cyberpunk workbench with supplied WolvenKit CLI support.
- Background execution and configured input/output/tool paths.


13. MUSIC PLAYER AND AI MUSIC CREATION
-------------------------------------
Music Player
- Directory-based music library browsing.
- Persistent playlists.
- Open/select songs from the library.
- Play, pause, stop, previous and next controls.
- Shuffle and repeat controls.
- Seek/progress feedback.
- Waveform artwork/visual feedback.
- Shared overall transport and playback visualization.
- Links between compatible current-track tools.
- Standalone Music launch batch.
- Initial-tool selection updates for the Music page.

AI Music Create
- Local prompt-based music creation through the configured engine.
- Generation length, BPM, key and meter controls.
- Language and output-format configuration where supported.
- Generation-step settings.
- Output-directory selection.
- Engine startup/status checks.
- Generate, stop, play and open-output actions.


14. SPLITTER
------------
- Vocal/instrumental stem separation through the configured Demucs workflow.
- Select a single song.
- Directory input for processing multiple songs.
- Output-folder selection.
- Demucs model selection.
- Background processing with progress feedback.
- Cancellation/stop handling.
- Suppressed processing console windows in updated Windows workers.
- Source song name included in exported stem filenames.
- Naming pattern: Song Name (Instrumental).wav and Song Name (Vocals).wav.
- No extra dash inserted before the parenthesized stem label.
- Per-song output folders use the song stem rather than retaining .mp3/.MP3.
- Updated output flow avoids creating split.log.


15. VOCALIST
------------
- Saved-voice library for local text-to-speech generation.
- Create a new voice entry.
- Import voice recordings from audio files, ZIPs or a directory.
- Add more samples to the currently selected voice.
- Store recordings and voice data in a local database/library.
- Recording-count and storage-size summaries.
- Analyze recordings and rebuild/improve saved speaker references.
- Reuse prior analyzed references when improving a voice.
- Preserve a previous working voice model/reference set when an update fails.
- Text prompting for speech generation.
- Text box without the previous 2,000-character UI cap.
- Long-input handling through the installed synthesis workflow.
- Expressiveness and voice-guidance controls.
- Auto, GPU and CPU device choices.
- Generated-audio playback and stop controls.
- Download/export generated WAV audio.
- Cancel jobs and view processing progress/status.
- Compact icon buttons in updated versions.
- Database-folder selection and existing-recording restoration controls.
- Local engine setup and saved configuration.
- Voice-library naming, including the project's JuiceWRLD entry.
- No recording-preview list or dedicated Import JuiceWRLD button in the revised UI.

The voice-improvement workflow builds/updates speaker conditioning from recordings;
it should not be described as full base-model training or automatic sung melody
generation. Generated quality depends on the installed engine and source samples.


16. AUTOTUNER
-------------
- Upload an isolated vocal recording.
- Detect vocal pitch and apply pitch correction.
- Chromatic correction to nearby semitones.
- Major/minor scale correction with a selected musical key.
- Correction-strength control.
- Retune-speed control.
- Maximum pitch-shift limit.
- Automatic, low-voice and high-voice pitch ranges.
- Corrected-audio preview/playback and stop controls.
- Corrected WAV output/export.
- Background worker/status feedback.
- Separate temporary outputs for repeated correction jobs in updated versions.
- Original uploaded recordings retained.
- Dependency setup through Setup_Autotuner.bat.


17. MUSIC INFO, METADATA AND PLAYBACK EFFECTS
-------------------------------------------
- Info tool tied to the current compatible music-player track.
- Open a song directly from Info.
- Details action to read song metadata.
- Edit title, artist, album, album artist, genre and date.
- Edit track/disc numbers, composer and supported album-sort fields.
- Save metadata back to the song with backup handling.
- Playback resume handling around supported metadata writes.
- Ten-band equalizer: 32, 64, 125, 250, 500 Hz; 1, 2, 4, 8 and 16 kHz.
- Preamp and per-band gain adjustment from -12 to +12 dB.
- Apply sound changes to current playback.
- Reset sound controls.
- Sound filters: Echo, Hallway, Tunnel, Stadium, Sewer, Auditorium and Speakers.
- Speed control from -10x to +10x, excluding zero.
- Negative speed/reverse processing in the supported playback-filter workflow.
- FFmpeg-backed audio processing.


18. CHORDS AND LEARNON
---------------------
- Music Chords workspace and chord-reference controls.
- Input and scan a local song.
- Chord, pitch/key and timing analysis through configured local analysis tools.
- Guitar fingering and fretboard visualization.
- Playback-synchronized chord/note displays.
- Perspective guitar-highway view.
- Piano keyboard highlighting from scanned pitches.
- Playback-synchronized drum estimates.
- Reference-note tuner independent of the main music player.
- Lyrics/word detection through configured transcription tools.
- Edit, append and clear detected words/lyrics.
- Genius lookup/link integration.
- Seek, restart, previous/next and play/pause actions.
- Local scan history and completed-analysis archive.
- Cache/index analyses by the audio file's revision.
- Save chord-song data and local .song references.
- Public song/reference lookup where configured.
- Visual color and instrument-board settings.
- Guitar Pro tablature conversion through the configured library.
- Rocksmith-related local audio conversion and arrangement export.


19. STUDIO AND INSTRUMENTS
-------------------------
- Unified Studio workspace in Design.
- Piano workspace and piano-roll note editing.
- Guitar workspace with fretboard/string/fret configuration.
- Guitar chord selection and strum/play interactions.
- Drums, Bass and Turntable workspaces.
- Vocals/recording workspace.
- Song/playlist arrangement view.
- MIDI-related workspace and import/export paths provided by the installed tool.
- Waveform view and visualization controls.
- Channel rack and pattern arrangement.
- Song blocks with editing, moving and removal.
- Pattern playback and song playback.
- Piano-roll playback/rendering and export.
- Pattern/channel mixer.
- Per-channel volume and pan.
- Mixer changes applied to arranged blocks without replacing their notes.
- Song audio export, including supported WAV/MP3 paths.
- Audio trimming, speed, gain, channels and fade controls.
- Instrument, root, scale, chord and octave settings where applicable.
- Saved Studio settings and compact icon navigation.


20. VIDEO
---------
- Video workspace with Timeline and Audio Sync tools.
- Timeline-based processing/editing through the installed Video tool.
- Audio/video input and output configuration.
- Align multiple screen captures against a shared soundtrack.
- Reference-view selection for synchronization.
- Audio offset analysis and manual offset adjustment.
- Crop controls for supported views.
- Per-view background/layout configuration.
- Export synchronized separate views.
- Save project/configuration data for supported sync workflows.
- Background scan/export jobs and status reporting.
- Clipchamp launch integration from the Video page.
- Reconstruction of videos from processed frames in the image pipeline.

Clipchamp is a launcher integration with Microsoft's application, not a bundled
replacement implementation of the entire Clipchamp editor.


21. DESIGN AND LAYOUT EDITING
----------------------------
- Layout Designer workspace.
- Layered blueprint/layout editing.
- Open reference images.
- New, open and save project actions.
- PNG export.
- Snap controls and color/style settings.
- Place supported layout items.
- Scan & Generate workflow for compatible inputs.
- UV-mapping related controls.
- Drawing information blocks and project information.
- Size/style settings and modern insert/item controls.
- Shared access to Studio, Image Editor, Icon Maker, 3D, Cabinet Builder,
  Sprite Skinner and DYI workspaces.


22. CABINET BUILDER
-------------------
Workspace and viewing
- Cabinet Builder workspace, historically labeled Cabinet Designer in some modules.
- Wall, Base and Both planning/view modes in the project updates.
- Floor/wall area sizing.
- Plan and 3D preview workflows.
- Current-layout and preview-layout views.
- Grid, camera/view and display controls.
- Zoom controls, mouse-wheel zoom and supported middle-mouse panning.
- Selection attributes, dimensions, position and elevation controls.
- GPU/CPU/memory feedback in supported 3D views.

Catalogs and items
- Catalog-driven cabinet/item library.
- Brand selection, select-all and deselect-all controls.
- Catalog/item indexing, search and discovery feedback.
- Catalog model assignment and nearest supported catalog-size selection.
- Item preview lists and drag-to-place interactions.
- Preview sizing/sorting preferences.
- Cabinets, doors, panels, corner cabinets, lazy Susan and trash-cabinet items
  where included in the installed catalogs.
- Appliance, window and obstacle placement categories.
- Cabinet-set alignment and supported random-plan generation.
- Overlap checks in supported placement/generation paths.

Editing
- Add/place items from previews.
- Move and rotate items.
- Rotation-angle controls and 90/180-degree actions.
- Resize and replace operations.
- Size-aware replacement filtering in the updated replacement workflow.
- Multi-selection and selection-rectangle interactions in supported views.
- Align, duplicate, rename and delete selected items.
- Elevation and dimension editing.
- Floor/wall images and material/finish controls.
- Texture scale, masks/recoloring and supported tiling preferences.
- Apply supported finishes/materials to selected items.
- Collapsible attributes and compact toolbar/settings layout.

Image Input
- Reference-image upload and embedded image-input workspace.
- Local OCR/Tesseract scanning.
- Multiple scanning passes and saved discovery results.
- Discovery progress and measurement-related analysis.
- Rotate and horizontal/vertical flip controls.
- Line, box and polygon selection tools in the project image-input workflow.
- Marker/highlighter tools and clear-selection controls.
- Catalog matching from detected dimensions and item information.
- Brand/finish-aware preview matching and placement into layout previews.
- Window/door/obstacle interpretation where supported by the installed analysis.

Saving and output
- Save/open layout/project workflows, including the project's .nxt layout format.
- UI/layout templates and saved workspace arrangements.
- Connected/reorderable toolbars in supported revisions.
- Movable/resizable workspace panels in the cabinet-specific UI.
- Blueprint, dimension and export-sheet workflows supplied by project modules.
- Camera/export and Blender rendering integrations where installed.
- Standalone Cabinet Builder launch/setup variants supplied during the project.


23. SPRITE SKINNER
------------------
- Load sprite sheets/reference poses.
- Detect and slice frames.
- RPG/template layout helpers.
- Single-character/template organization.
- Pose/frame assignment and named clip scanning.
- Frame-positioning and guide-line adjustment.
- Reskin/reference-frame workflow.
- Sprite-frame preview and zoom.
- Horizontal flipping.
- Animation playback and timing preview.
- Save named clips and export sprite assets.


24. DYI PROJECT ASSISTANT
------------------------
- Add reference images or directories.
- Optional recursive image import.
- Image selection, fit and zoom.
- Local OCR passes and saved pass/reference history.
- Optional local AI scan/generation through configured models.
- Editable project instructions and ordered steps.
- Add, remove, reorder and edit steps.
- Materials/tools lists.
- Apply step edits to the project.
- Generate, preview and save PDF output.
- Previous/next PDF page navigation and refreshed previews.
- Save and reopen projects.
- Setup/model settings, cancellation and background job feedback.


25. JUICEWRLD MEDIA LIBRARY
--------------------------
- Local song/media browsing.
- Folder selection and media scanning.
- Open/play local files.
- Songs, albums and related catalogue views.
- Sourced offline album/reference catalogue.
- Release and sales source links where provided.
- Shared Home/player controls and spectrum integration.
- Studio/Drive-file browser integration.
- ZIP directory previews.
- Explicit local downloads through the supplied workflow.

This media-library page is separate from the Vocalist voice database entry.


26. FOOD - RECIPE MAKER
----------------------
- Food is a main application page.
- Recipe Maker and Meal Maker are Food subtools.
- Local archive of 3,634 meals from the supplied cookbook collection.
- Search by meal name and ingredient text.
- Cookbook and category filters.
- Meal name, yield/servings and category fields.
- Ingredients displayed for a selected meal.
- Expanded Preparation editor.
- Available cookbook directions displayed as ordered, numbered steps.
- Preparation supplied for 3,342 archived entries in the current archive update.
- Source guidance for entries without reliably extracted directions.
- Original recipe/cookbook source links and PDF-page references.
- Cookbook/source overview.
- Create new personal recipes.
- Copy an archived recipe into a personal version.
- Edit and save ingredients and preparation notes.
- Local SQLite recipe storage.
- Preserve personal records separately from the cookbook archive.
- Keep in-session drafts when switching between recipe entries.
- Delete personal recipes without deleting archive recipes.
- Export recipe/ingredient data as text or JSON.
- Estimate Cost button replacing the older ingredient checklist button.
- Removal of the redundant Food header and Cooking/provenance block above
  Preparation in the relevant updates.
- First-open Recipe Maker activation repair in V329.


27. FOOD - MEAL MAKER AND TIMER
------------------------------
- Upload up to five ingredient photos for one scan.
- Individual image upload boxes with previews.
- Replace or remove uploaded images.
- Local vision-model scanning in the configured Windows workflow.
- Detected ingredients shown in an editable list/viewport.
- Add, edit or remove ingredients manually.
- Create meal ideas from available ingredient types.
- Compare the list against the archived recipes.
- Show matched ingredients and additional ingredients needed.
- Optional pantry staples: water, salt, pepper and oil.
- Open/view the source recipe for a suggested meal.
- No claim that visual item matching proves sufficient ingredient quantities.
- Kitchen countdown timer with a specified duration.
- Start/resume, pause and reset controls.
- Alert sound at expiry and alert testing where provided.
- Timer retained independently of recipe scanning/meal selection.


28. FOOD - INGREDIENT COST ESTIMATES
----------------------------------
- Select Meijer, Target, Walmart, Kroger, Aldi, Dollar General or Family Dollar.
- Check publicly readable current product offers.
- Show matched product/package, package count, unit/package price and line cost.
- Display a total above the price table.
- Automatically choose a suitable supported product match in the Windows update.
- No requirement to open store search just to display an available price.
- Editable product choice, package count and manual price.
- Price-source link and checked timestamp.
- Local SQLite history of observed and manually entered prices.
- Reuse previous matching prices when live lookup fails.
- Same-store historical prices preferred over another store's history.
- Explicit other-store labels when an estimate uses another retailer's history.
- Historical/manual estimates marked with a tilde and estimate status.
- Show previous estimates immediately while refreshing live prices.
- Initial reference history containing 22 observed common-grocery quotes.
- Filter cookbook page/footer text out of the ingredient price check.
- Distinguish live prices, estimates and items without price history.
- Partial-total labeling when some ingredients cannot be priced.
- Cancel lookup jobs and reject stale results after store changes.
- Export estimates with source/status information.
- Optional direct store search and source-opening actions remain available.

These are whole-package estimates, not automatic recipe-portion costing.
Taxes, delivery fees, deposits, coupons and package-unit conversion are excluded.
Public retailer access and local prices vary; no missing price is invented.


29. FOOD FOR ANDROID - SEPARATE COMPANION APP
--------------------------------------------
- Standalone signed APK; Windows AI Generator is not needed to run it.
- Touch-friendly phone interface and wider tablet layout.
- Recipe Maker, Meal Maker and Timer navigation.
- Bundled offline recipe archive and available preparation directions.
- Meal and ingredient search, cookbook/category filters and paging.
- Favorite recipes.
- Save personal recipes, preparation notes and drafts on the device.
- Export/restore personal-data backups through Android's document picker.
- Five image slots with previews and local image selection/resizing.
- Editable ingredient suggestions and local meal matching.
- Native timer scheduling, notification alerts and foreground sound.
- Android notification/precise-alarm settings access.
- Cost-estimate interface with the seven retailer choices and online price lookup.
- Same package/signing identity for in-place updates from the earlier Food APK.

Offline scanning in Android 1.0.328
- Bundled ARM64 llama.cpp CPU inference engine.
- Bundled SmolVLM-500M Q8 language model and image projector.
- Model files included in the APK; no separate runtime download required.
- First-scan local extraction/preparation and SHA-256 verification.
- Optional Prepare offline model action in Settings.
- No internet, Wi-Fi, computer or Ollama server required for photo scanning.
- Food-presence check before ingredient extraction.
- Ingredient-name extraction from model output.
- Filtering of speculative caption alternatives and redundant ingredient names.
- Image-by-image processing and progress feedback.
- Cancel scan without overwriting the prior ingredient list.
- Unload model/working context after the scan to release memory.
- Targeted to ARM64 devices such as the user's Samsung Galaxy S23+.
- Native library uses 16 KB ELF LOAD alignment.
- Installer size is approximately 525 MB because model weights are included.
- Source/rebuild package with model-restoration helper and setup instructions.

The compact vision model can miss or misidentify items; the list stays editable.
Fresh store-price checks still require internet. The Windows V327 price-history
feature and Android price UI are separate implementations. Android signature,
packaging, host inference and mobile UI checks were performed; physical S23+
installation/native-inference testing was not available in this workspace.


30. INTEGRATION AND OFFLINE-USE NOTES
-----------------------------------
- Local files, saved projects and supported native editors can work without web
  access once their required dependencies are installed.
- Windows local AI tools require their configured engines/models; they are not
  all bundled into the base application.
- Android Food 1.0.328 specifically bundles its offline scanning engine/model.
- External cloud/provider integrations need compatible credentials/connectivity.
- Live price checks, web searches, online covers, source lookups and downloads
  need internet access.
- Blender, FFmpeg, COLMAP, RenderDoc, Noesis, QuickBMS, 3DSimED, game SDKs,
  emulators and proprietary utilities are separate dependencies where used.
- A configured engine/game workspace is not a promise of support for every
  proprietary archive revision, skeleton, texture format or game release.
- Installed catalog/model/script collections determine available item counts,
  file formats, inference choices and conversion coverage.
- Existing code and completed updates were inventoried; this document is a
  feature reference rather than a claim that every external integration was
  tested on the user's installed machine.



