# CLI Workflow

### Main Loop & Menus
- **File:** `cliper.py`
- **Functions:** `main()`, `menu_principal()`, `opcion_procesar_video()`
- **Purpose:** Rich-based interactive CLI that orchestrates the pipeline.
- **Capabilities:** Lists downloaded videos with state, opens per-video actions, entry to add/import videos, cleanup shortcuts, and a "Full Pipeline" menu item (currently shows *coming soon* and is not implemented).

### Add or Import Video
- **Function:** `opcion_descargar_video()`
- **Purpose:** Add a YouTube URL **or** register a local file path.
- **Flow:** Validates input → lets user pick a content preset → downloads if URL or registers existing file → stores `content_type` + `preset` in `StateManager` → optional immediate transcription.

### Per-Video Actions
- **Functions:** `opcion_transcribir_video()`, `opcion_generar_clips()`, `opcion_generar_copies()`, `opcion_exportar_clips()`
- **Purpose:** Guided steps for each pipeline stage using preset-driven defaults.
- **Highlights:** Model selection with shortcuts, language "auto" mapping, clip duration presets (short/medium/long/custom), adjustable max clips, copy generation gating on clips, export options for aspect ratio, subtitles, face tracking (9:16), logo overlay, and organize-by-style folders based on AI classifications.

### Cleanup Shortcuts
- **Functions:** `opcion_cleanup_project()`, `cleanup_downloads()`, `cleanup_transcripts()`, `cleanup_clips_metadata()`, `cleanup_outputs()`, `cleanup_entire_project()`
- **Purpose:** CLI wrappers around `CleanupManager` to delete specific artifact types, outputs only, or perform a guarded full reset.
