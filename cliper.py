# -*- coding: utf-8 -*-
"""
CLIPER - CLI Principal Unificado
Developed by opino.tech | Powered by AI | CDMX

Este es el punto de entrada principal del proyecto.
Orquesta todo el pipeline: download → transcribe → generate clips → resize
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Rich para interfaz profesional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich import box

# Mis módulos
try:
    from src.downloader import YoutubeDownloader
    from src.transcriber import Transcriber
    from src.clips_generator import ClipsGenerator
    from src.video_exporter import VideoExporter
    from src.copys_generator import generate_copys_for_video
    from src.cleanup_manager import CleanupManager
    from src.utils import get_state_manager
    from src.utils.logo import (
        DEFAULT_BUILTIN_LOGO_PATH,
        is_valid_logo_location,
        normalize_logo_setting_value,
        resolve_logo_path,
    )
    from src.utils.video_registry import (
        SUPPORTED_VIDEO_EXTENSIONS,
        collect_local_video_paths as _shared_collect_local_video_paths,
        compute_unique_video_id as _compute_unique_video_id,
        is_supported_video_file as _is_supported_video_file,
        load_registered_videos,
    )
    from config.content_presets import get_preset, list_presets, get_preset_description
except ImportError as e:
    print(f"Error importando módulos: {e}")
    print("Ejecuta desde la raíz del proyecto: uv run cliper.py")
    sys.exit(1)

# Console de Rich
console = Console()


def _parse_video_selection(selection: str, max_index: int) -> List[int]:
    """
    Parse selections like: 'all', '1,3,5-7'
    Returns 0-based indices (sorted, unique).
    """
    sel = (selection or "").strip().lower()
    if not sel:
        return []
    if sel in {"all", "*"}:
        return list(range(max_index))

    indices: set[int] = set()
    parts = [p.strip() for p in sel.split(",") if p.strip()]
    for part in parts:
        if "-" in part:
            a, b = [x.strip() for x in part.split("-", 1)]
            if not a.isdigit() or not b.isdigit():
                continue
            start = int(a)
            end = int(b)
            if start > end:
                start, end = end, start
            for i in range(start, end + 1):
                if 1 <= i <= max_index:
                    indices.add(i - 1)
        else:
            if part.isdigit():
                i = int(part)
                if 1 <= i <= max_index:
                    indices.add(i - 1)

    return sorted(indices)


def _collect_local_video_paths(input_str: str) -> Tuple[List[Path], List[str]]:
    """
    Accepts:
    - A file path
    - A folder path (adds supported video files inside)
    - Multiple paths separated by commas
    """
    raw = (input_str or "").strip()
    if not raw:
        return [], ["No input provided"]

    candidates: List[str] = [p.strip() for p in raw.split(",") if p.strip()]
    all_paths: List[Path] = []
    errors: List[str] = []

    for candidate in candidates:
        normalized = candidate.strip().strip('"').strip("'")
        p = Path(normalized).expanduser()
        if not p.exists():
            errors.append(f"Path not found: {candidate}")
            continue

        if p.is_dir():
            include_subfolders = Confirm.ask(
                f"[cyan]Include subfolders for '{p}'?[/cyan]",
                default=False
            )
            paths, errs = _shared_collect_local_video_paths(str(p), recursive=include_subfolders)
        else:
            paths, errs = _shared_collect_local_video_paths(str(p))

        all_paths.extend(paths)
        errors.extend(errs)

    unique: List[Path] = []
    seen: set[str] = set()
    for p in all_paths:
        try:
            key = str(p.resolve())
        except Exception:
            key = str(p)
        if key not in seen:
            seen.add(key)
            unique.append(p)

    return unique, errors


def cargar_videos_disponibles(state_manager) -> List[Dict[str, str]]:
    """
    Fuente única de verdad para el UI:
    - Descubre videos en downloads/ y los registra/actualiza en el state.
    - Incluye videos registrados con ruta fuera del proyecto.
    - Solo retorna videos cuyo archivo existe actualmente.
    """
    return load_registered_videos(state_manager)


def mostrar_banner():
    """
    Banner principal de CLIPER
    """
    console.clear()

    logo = Text()
    logo.append("CLIPER", style="bold cyan")
    logo.append(" | Video Clipper\n", style="white")
    logo.append("Transform long videos into viral clips", style="dim")
    logo.justify = "center"

    footer = Text()
    footer.append("Developed by ", style="dim")
    footer.append("opino.tech", style="bold magenta")
    footer.append(" | Powered by ", style="dim")
    footer.append("AI", style="bold green")
    footer.append(" | ", style="dim")
    footer.append("CDMX", style="bold yellow")

    panel = Panel(
        logo,
        title="[bold white]Welcome[/bold white]",
        subtitle=footer,
        border_style="cyan",
        box=box.DOUBLE
    )

    console.print(panel)
    console.print()


def escanear_videos() -> List[Dict[str, str]]:
    """
    Escaneo la carpeta downloads/ para encontrar videos MP4

    Retorno lista de dicts con info de cada video:
    [
        {
            "filename": "video.mp4",
            "path": "downloads/video.mp4",
            "video_id": "video_abc123"  # ID único basado en nombre
        }
    ]
    """
    downloads_dir = Path("downloads")

    if not downloads_dir.exists():
        downloads_dir.mkdir(parents=True, exist_ok=True)
        return []

    # Busco todos los archivos .mp4 (case-insensitive: .mp4 y .MP4)
    videos = []
    # Combinamos ambos patrones para cubrir mayúsculas y minúsculas
    video_files = set(downloads_dir.glob("*.mp4")) | set(downloads_dir.glob("*.MP4"))
    
    for video_file in video_files:
        # Genero un ID único para el video (el nombre sin extensión)
        video_id = video_file.stem  # "AI CDMX Live Stream_gjPVlCHU9OM"

        videos.append({
            "filename": video_file.name,
            "path": str(video_file),
            "video_id": video_id
        })

    return videos


def mostrar_videos_disponibles(videos: List[Dict], state_manager) -> Optional[Table]:
    """
    Muestro una tabla con los videos disponibles y su estado

    Retorno la tabla (o None si no hay videos)
    """
    if not videos:
        return None

    # Creo la tabla
    table = Table(
        show_header=True,
        header_style="bold cyan",
        box=box.ROUNDED,
        border_style="cyan"
    )

    table.add_column("#", style="bold cyan", width=4)
    table.add_column("Video Name", style="white")
    table.add_column("Status", style="green")

    # Agrego cada video a la tabla
    for idx, video in enumerate(videos, 1):
        video_id = video['video_id']

        # Obtengo el estado del video
        state = state_manager.get_video_state(video_id)

        if state:
            # Construyo el status basado en el progreso
            status_parts = []
            if state['transcribed']:
                status_parts.append("[green]Transcribed ✓[/green]")
            if state['clips_generated']:
                status_parts.append(f"[green]{len(state['clips'])} clips[/green]")

            if not status_parts:
                status = "[yellow]Downloaded[/yellow]"
            else:
                status = " | ".join(status_parts)
        else:
            status = "[yellow]Downloaded[/yellow]"

        # Nombre corto (trunco si es muy largo)
        display_name = video['filename']
        if len(display_name) > 40:
            display_name = display_name[:37] + "..."

        table.add_row(str(idx), display_name, status)

    return table


def menu_principal(videos: List[Dict], state_manager) -> str:
    """
    Muestro el menú principal y retorno la opción elegida
    """
    # Si hay videos, muestro la tabla
    if videos:
        console.print("[bold]Available Videos:[/bold]\n")
        table = mostrar_videos_disponibles(videos, state_manager)
        if table:
            console.print(table)
            console.print()

    # Creo el menú
    menu_table = Table(
        show_header=False,
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 2)
    )

    menu_table.add_column("Option", style="bold cyan", width=8)
    menu_table.add_column("Description", style="white")

    if videos:
        menu_table.add_row("1", "Process a video")
        menu_table.add_row("2", "Batch process videos")
        menu_table.add_row("3", "Add/Download video(s)")
        menu_table.add_row("4", "Cleanup project data")
        menu_table.add_row("5", "Exit")
        opciones = ["1", "2", "3", "4", "5"]
    else:
        menu_table.add_row("1", "Add/Download video(s)")
        menu_table.add_row("2", "Cleanup project data")
        menu_table.add_row("3", "Exit")
        opciones = ["1", "2", "3"]

    console.print(Panel(menu_table, title="[bold]Main Menu[/bold]", border_style="cyan"))
    console.print()

    opcion = Prompt.ask(
        "[bold cyan]Choose an option[/bold cyan]",
        choices=opciones,
        default=opciones[0]
    )

    return opcion


def opcion_descargar_video(downloader, state_manager):
    """
    Descargo un nuevo video de YouTube
    """
    console.clear()
    mostrar_banner()

    console.print(Panel(
        "[bold]Add Video(s)[/bold]\n"
        "Provide a YouTube URL, a local file path, a folder path, or multiple paths (comma-separated).",
        border_style="cyan"
    ))
    console.print()

    input_str = Prompt.ask("[cyan]YouTube URL or file/folder path[/cyan]").strip()

    if not input_str:
        console.print("[red]Error: No input provided[/red]")
        Prompt.ask("\n[dim]Press ENTER to continue[/dim]", default="")
        return

    # Detect if it's a URL or local input
    is_url = input_str.startswith(('http://', 'https://', 'www.', 'youtube.com', 'youtu.be'))
    is_local = not is_url

    # Ask for content type
    console.print()
    console.print("[bold]Content Type[/bold]")
    console.print("[dim]This helps optimize transcription and clip generation[/dim]\n")

    presets = list_presets()
    presets_table = Table(show_header=False, box=None, padding=(0, 2))
    presets_table.add_column(style="cyan", width=6)
    presets_table.add_column(style="white")
    presets_table.add_column(style="dim")

    preset_keys = list(presets.keys())
    for idx, (key, name) in enumerate(presets.items(), 1):
        description = get_preset_description(key)
        presets_table.add_row(str(idx), name, description)

    console.print(presets_table)
    console.print()

    content_choice = Prompt.ask(
        "[cyan]Select content type[/cyan]",
        choices=[str(i) for i in range(1, len(presets) + 1)],
        default="3"
    )

    content_type = preset_keys[int(content_choice) - 1]
    preset = get_preset(content_type)

    console.print(f"\n[green]✓ Selected:[/green] {presets[content_type]}")
    console.print(f"[dim]{preset['use_case']}[/dim]")

    console.print()

    try:
        added_videos: List[Dict[str, str]] = []

        if is_url:
            # Download from YouTube
            with console.status("[cyan]Downloading video...[/cyan]", spinner="dots"):
                downloaded_path = downloader.download(input_str, quality="best")

            if not downloaded_path:
                console.print(Panel(
                    "[red]Download failed. Check the logs above.[/red]",
                    border_style="red"
                ))
                console.print()
                Prompt.ask("[dim]Press ENTER to return to menu[/dim]", default="")
                return

            video_file = Path(downloaded_path)
            video_id = _compute_unique_video_id(video_file, state_manager)

            state_manager.register_video(
                video_id=video_id,
                filename=video_file.name,
                video_path=str(video_file),
                content_type=content_type,
                preset=preset
            )
            added_videos.append({"filename": video_file.name, "path": str(video_file), "video_id": video_id})
        elif is_local:
            local_paths, errors = _collect_local_video_paths(input_str)
            if errors:
                console.print()
                console.print("[yellow]Input warnings:[/yellow]")
                for e in errors[:10]:
                    console.print(f"[dim]- {e}[/dim]")
                if len(errors) > 10:
                    console.print(f"[dim]... and {len(errors) - 10} more[/dim]")

            if not local_paths:
                console.print("\n[red]Error: No valid video files found[/red]")
                Prompt.ask("\n[dim]Press ENTER to continue[/dim]", default="")
                return

            for p in local_paths:
                abs_path = p.expanduser().resolve()
                video_id = _compute_unique_video_id(abs_path, state_manager)
                state_manager.register_video(
                    video_id=video_id,
                    filename=abs_path.name,
                    video_path=str(abs_path),
                    content_type=content_type,
                    preset=preset
                )
                added_videos.append({"filename": abs_path.name, "path": str(abs_path), "video_id": video_id})

        console.clear()
        mostrar_banner()

        if len(added_videos) == 1:
            v = added_videos[0]
            panel_body = (
                f"[green]✓ Video added successfully[/green]\n\n"
                f"File: {v['filename']}\n"
                f"Location: {v['path']}"
            )
        else:
            sample = "\n".join([f"• {v['filename']}" for v in added_videos[:5]])
            panel_body = (
                f"[green]✓ Videos added successfully[/green]\n\n"
                f"Added: {len(added_videos)} video(s)\n\n"
                f"{sample}"
            )
            if len(added_videos) > 5:
                panel_body += f"\n[dim]... and {len(added_videos) - 5} more[/dim]"

        console.print(Panel(
            panel_body,
            title="[bold green]Success[/bold green]",
            border_style="green"
        ))

        # Optional immediate batch processing
        console.print()
        if Confirm.ask("[cyan]Batch process these videos now?[/cyan]", default=False):
            opcion_procesar_videos_en_lote(
                videos=cargar_videos_disponibles(state_manager),
                state_manager=state_manager,
                preselected_video_ids=[v["video_id"] for v in added_videos]
            )
            return

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")

    console.print()
    Prompt.ask("[dim]Press ENTER to return to menu[/dim]", default="")


def opcion_procesar_video(videos: List[Dict], state_manager):
    """
    Proceso un video existente (transcribir, generar clips, etc.)
    """
    console.clear()
    mostrar_banner()

    console.print("[bold]Select a video to process:[/bold]\n")

    # Muestro los videos numerados
    for idx, video in enumerate(videos, 1):
        console.print(f"  {idx}. {video['filename']}")

    console.print()

    # Pido al usuario que elija
    seleccion = Prompt.ask(
        "[cyan]Video number[/cyan]",
        choices=[str(i) for i in range(1, len(videos) + 1)]
    )

    video_seleccionado = videos[int(seleccion) - 1]
    video_id = video_seleccionado['video_id']

    # Loop infinito para refrescar el menu después de cada acción
    while True:
        # Obtengo el estado del video (refrescado en cada iteración)
        state = state_manager.get_video_state(video_id)

        # Limpio la pantalla y muestro banner
        console.clear()
        mostrar_banner()

        # Muestro opciones según el estado
        console.print(f"\n[bold]Processing: {video_seleccionado['filename']}[/bold]\n")

        # Muestro el estado actual
        if state:
            status_parts = []
            if state['transcribed']:
                status_parts.append("[green]✓ Transcribed[/green]")
            if state['clips_generated']:
                num_clips = len(state.get('clips', []))
                status_parts.append(f"[green]✓ {num_clips} clips generated[/green]")
            if state.get('clips_exported', False):
                num_exported = len(state.get('exported_clips', []))
                aspect = state.get('export_aspect_ratio', 'original')
                status_parts.append(f"[green]✓ {num_exported} clips exported ({aspect})[/green]")

            if status_parts:
                console.print("Status: " + " | ".join(status_parts))
                console.print()

        # Creo menú de acciones disponibles
        actions_table = Table(show_header=False, box=box.ROUNDED, border_style="cyan", padding=(0, 2))
        actions_table.add_column("Option", style="bold cyan", width=8)
        actions_table.add_column("Description", style="white")

        actions = []

        if state and state['transcribed']:
            actions.append(("1", "Re-transcribe video"))
            actions.append(("2", "Generate/Regenerate clips"))

            # Si ya tengo clips, ofrezco más opciones
            if state.get('clips_generated', False):
                actions.append(("3", "Generate AI copies (auto-classify + captions)"))
                actions.append(("4", "Export clips to video files"))
                actions.append(("5", "Back to menu"))
            else:
                actions.append(("3", "Back to menu"))
        else:
            actions.append(("1", "Transcribe video"))
            actions.append(("2", "Back to menu"))

        for option, desc in actions:
            actions_table.add_row(option, desc)

        console.print(actions_table)
        console.print()

        choices = [opt for opt, _ in actions]
        action = Prompt.ask(
            "[bold cyan]Choose an action[/bold cyan]",
            choices=choices,
            default=choices[0]
        )

        # Ejecuto la acción elegida
        if state and state['transcribed']:
            if action == "1":
                opcion_transcribir_video(video_seleccionado, state_manager)
                # Continúa el loop para refrescar el menu
            elif action == "2":
                opcion_generar_clips(video_seleccionado, state_manager)
                # Continúa el loop para refrescar el menu
            elif action == "3":
                if state['clips_generated']:
                    opcion_generar_copies(video_seleccionado, state_manager)
                    # Continúa el loop para refrescar el menu
                else:
                    return  # Back to main menu
            elif action == "4":
                if state['clips_generated']:
                    opcion_exportar_clips(video_seleccionado, state_manager)
                    # Continúa el loop para refrescar el menu
                else:
                    return  # Back to main menu
            elif action == "5":
                return  # Back to main menu
        else:
            if action == "1":
                opcion_transcribir_video(video_seleccionado, state_manager)
                # Continúa el loop para refrescar el menu
            elif action == "2":
                return  # Back to main menu


def opcion_procesar_videos_en_lote(
    videos: List[Dict],
    state_manager,
    preselected_video_ids: Optional[List[str]] = None
):
    """
    Procesa múltiples videos con la misma configuración (transcribe/generate/export).
    """
    console.clear()
    mostrar_banner()

    if not videos:
        console.print("[yellow]No videos available[/yellow]")
        Prompt.ask("\n[dim]Press ENTER to return[/dim]", default="")
        return

    if preselected_video_ids:
        by_id = {v["video_id"]: v for v in videos}
        selected = [by_id[vid] for vid in preselected_video_ids if vid in by_id]
    else:
        console.print("[bold]Select videos to process:[/bold]\n")
        for idx, video in enumerate(videos, 1):
            console.print(f"  {idx}. {video['filename']}")
        console.print()

        selection = Prompt.ask(
            "[cyan]Selection (e.g. 1,3-5 or 'all')[/cyan]",
            default="all"
        )
        indices = _parse_video_selection(selection, len(videos))
        selected = [videos[i] for i in indices]

    if not selected:
        console.print("[yellow]No videos selected[/yellow]")
        Prompt.ask("\n[dim]Press ENTER to return[/dim]", default="")
        return

    console.clear()
    mostrar_banner()

    console.print(Panel(
        f"[bold]Batch Processing[/bold]\n\nSelected: {len(selected)} video(s)",
        border_style="cyan"
    ))
    console.print()

    actions_table = Table(show_header=False, box=box.ROUNDED, border_style="cyan", padding=(0, 2))
    actions_table.add_column("Option", style="bold cyan", width=8)
    actions_table.add_column("Description", style="white")
    actions_table.add_row("1", "Transcribe all (same model/language)")
    actions_table.add_row("2", "Generate clips all (same durations)")
    actions_table.add_row("3", "Export clips all (same export settings)")
    actions_table.add_row("4", "Back")
    console.print(actions_table)
    console.print()

    action = Prompt.ask("[bold cyan]Choose an action[/bold cyan]", choices=["1", "2", "3", "4"], default="1")
    if action == "4":
        return

    if action == "1":
        _batch_transcribe(selected, state_manager)
    elif action == "2":
        _batch_generate_clips(selected, state_manager)
    elif action == "3":
        _batch_export_clips(selected, state_manager)


def _batch_transcribe(selected: List[Dict[str, str]], state_manager):
    console.print("[bold]Transcription Settings:[/bold]\n")

    model_options = Table(show_header=False, box=None, padding=(0, 2))
    model_options.add_column(style="cyan")
    model_options.add_column(style="white")
    model_options.add_column(style="dim")
    model_options.add_row("\\[t]iny", "Fastest", "~1min for 1hr video")
    model_options.add_row("\\[b]ase", "Balanced", "~5min for 1hr video")
    model_options.add_row("\\[s]mall", "Accurate", "~10min for 1hr video")
    model_options.add_row("\\[m]edium", "Very accurate", "~20min for 1hr video")
    console.print(model_options)
    console.print()

    shortcut_map = {"t": "tiny", "b": "base", "s": "small", "m": "medium"}
    valid_inputs = ["tiny", "base", "small", "medium", "t", "b", "s", "m"]
    model_input = Prompt.ask("[cyan]Model size[/cyan]", choices=valid_inputs, default="base")
    model_size = shortcut_map.get(model_input, model_input)

    console.print()
    language_input = Prompt.ask("[cyan]Language (or 'auto' to detect)[/cyan]", default="auto").strip()
    language = None if language_input.lower() == "auto" else language_input

    skip_done = Confirm.ask("[cyan]Skip videos already transcribed?[/cyan]", default=True)

    console.print()
    if not Confirm.ask(f"[cyan]Start transcription for {len(selected)} video(s)?[/cyan]", default=True):
        console.print("[yellow]Cancelled[/yellow]")
        return

    console.print("\n[cyan]Loading Whisper model...[/cyan]")
    transcriber = Transcriber(model_size=model_size)

    ok = 0
    skipped = 0
    failed = 0
    for video in selected:
        video_id = video["video_id"]
        state = state_manager.get_video_state(video_id) or {}
        if skip_done and state.get("transcribed"):
            skipped += 1
            console.print(f"[dim]Skipping (already transcribed): {video['filename']}[/dim]")
            continue

        try:
            console.print(f"\n[cyan]Transcribing: {video['filename']}[/cyan]")
            transcript_path = transcriber.transcribe(
                video_path=video["path"],
                language=language,
                skip_if_exists=False
            )
            if transcript_path:
                state_manager.mark_transcribed(video_id, transcript_path)
                ok += 1
            else:
                failed += 1
        except KeyboardInterrupt:
            raise
        except Exception as e:
            failed += 1
            console.print(f"[red]Failed: {video['filename']} → {e}[/red]")

    console.print()
    console.print(Panel(
        f"[green]Done[/green]\n\n"
        f"Transcribed: {ok}\n"
        f"Skipped: {skipped}\n"
        f"Failed: {failed}",
        border_style="green" if failed == 0 else "yellow"
    ))

    console.print()
    Prompt.ask("[dim]Press ENTER to return[/dim]", default="")


def _batch_generate_clips(selected: List[Dict[str, str]], state_manager):
    console.print("[bold]Clip Generation Settings:[/bold]\n")

    duration_options = Table(show_header=False, box=None, padding=(0, 2))
    duration_options.add_column(style="cyan")
    duration_options.add_column(style="white")
    duration_options.add_column(style="dim")
    duration_options.add_row("1", "Short clips", "30-60s (TikTok/Shorts)")
    duration_options.add_row("2", "Medium clips", "30-90s (Reels/Stories)")
    duration_options.add_row("3", "Long clips", "60-180s (YouTube)")
    duration_options.add_row("4", "Custom", "Enter min/max seconds")
    console.print(duration_options)
    console.print()

    duration_choice = Prompt.ask("[cyan]Clip duration preset[/cyan]", choices=["1", "2", "3", "4"], default="2")
    presets = {"1": (30, 60), "2": (30, 90), "3": (60, 180)}
    if duration_choice in presets:
        min_duration, max_duration = presets[duration_choice]
    else:
        min_duration = int(Prompt.ask("[cyan]Min clip seconds[/cyan]", default="30"))
        max_duration = int(Prompt.ask("[cyan]Max clip seconds[/cyan]", default="90"))

    console.print()
    max_clips = int(Prompt.ask("[cyan]Maximum number of clips to generate[/cyan]", default="100"))

    skip_done = Confirm.ask("[cyan]Skip videos that already have clips?[/cyan]", default=True)

    console.print()
    if not Confirm.ask(f"[cyan]Start clip generation for {len(selected)} video(s)?[/cyan]", default=True):
        console.print("[yellow]Cancelled[/yellow]")
        return

    console.print("\n[cyan]Initializing ClipsAI...[/cyan]")
    clips_gen = ClipsGenerator(min_clip_duration=min_duration, max_clip_duration=max_duration)

    ok = 0
    skipped = 0
    failed = 0
    for video in selected:
        video_id = video["video_id"]
        state = state_manager.get_video_state(video_id) or {}
        if skip_done and state.get("clips_generated"):
            skipped += 1
            console.print(f"[dim]Skipping (already has clips): {video['filename']}[/dim]")
            continue

        transcript_path = state.get("transcript_path") or state.get("transcription_path")
        if not transcript_path or not Path(transcript_path).exists():
            skipped += 1
            console.print(f"[yellow]Skipping (no transcript): {video['filename']}[/yellow]")
            continue

        try:
            console.print(f"\n[cyan]Generating clips: {video['filename']}[/cyan]")
            clips = clips_gen.generate_clips(
                transcript_path=transcript_path,
                min_clips=3,
                max_clips=max_clips
            )
            if clips:
                clips_metadata_path = clips_gen.save_clips_metadata(clips=clips, video_id=video_id)
                state_manager.mark_clips_generated(video_id, clips, clips_metadata_path)
                ok += 1
            else:
                failed += 1
        except KeyboardInterrupt:
            raise
        except Exception as e:
            failed += 1
            console.print(f"[red]Failed: {video['filename']} → {e}[/red]")

    console.print()
    console.print(Panel(
        f"[green]Done[/green]\n\n"
        f"Clips generated: {ok}\n"
        f"Skipped: {skipped}\n"
        f"Failed: {failed}",
        border_style="green" if failed == 0 else "yellow"
    ))

    console.print()
    Prompt.ask("[dim]Press ENTER to return[/dim]", default="")


def _load_clip_styles_if_present(video_id: str) -> Optional[Dict[int, str]]:
    copys_file = Path("output") / video_id / "copys" / "clips_copys.json"
    if not copys_file.exists():
        return None
    try:
        import json
        with open(copys_file, "r", encoding="utf-8") as f:
            copys_data = json.load(f)
        classifications = copys_data.get("classification_metadata", {}).get("classifications", [])
        if not classifications:
            return None
        return {int(c["clip_id"]): c["style"] for c in classifications if "clip_id" in c and "style" in c}
    except Exception:
        return None


def _batch_export_clips(selected: List[Dict[str, str]], state_manager):
    console.print("[bold]Export Settings:[/bold]\n")

    aspect_options = Table(show_header=False, box=None, padding=(0, 2))
    aspect_options.add_column(style="cyan")
    aspect_options.add_column(style="white")
    aspect_options.add_column(style="dim")
    aspect_options.add_row("1", "Original", "Keep video aspect ratio (usually 16:9)")
    aspect_options.add_row("2", "Vertical (9:16)", "For TikTok, Reels, Shorts")
    aspect_options.add_row("3", "Square (1:1)", "For Instagram posts")
    console.print(aspect_options)
    console.print()

    aspect_choice = Prompt.ask("[cyan]Aspect ratio[/cyan]", choices=["1", "2", "3"], default="2")
    aspect_map = {"1": None, "2": "9:16", "3": "1:1"}
    aspect_ratio = aspect_map[aspect_choice]

    enable_face_tracking = False
    face_tracking_strategy = "keep_in_frame"
    face_tracking_sample_rate = 3
    if aspect_ratio == "9:16":
        console.print()
        enable_face_tracking = Confirm.ask("[cyan]Enable AI face tracking (vertical only)?[/cyan]", default=False)
        if enable_face_tracking:
            console.print()
            face_style = Prompt.ask("[cyan]Face tracking style[/cyan]", choices=["1", "2"], default="1")
            face_tracking_strategy = "keep_in_frame" if face_style == "1" else "centered"
            console.print()
            advanced = Confirm.ask("[dim]Configure advanced sampling rate?[/dim]", default=False)
            if advanced:
                face_tracking_sample_rate = int(Prompt.ask("Frame sample rate (every N frames)", default="3"))

    console.print()
    add_logo = Confirm.ask("[cyan]Add logo overlay to clips?[/cyan]", default=False)
    saved_logo_path = state_manager.get_setting("logo_path", DEFAULT_BUILTIN_LOGO_PATH)
    logo_path = saved_logo_path
    logo_position = "top-right"
    logo_scale = 0.1
    if add_logo:
        console.print(f"[dim]Current default logo location:[/dim] {saved_logo_path}")
        logo_path = Prompt.ask("Logo file path (or directory)", default=logo_path)
        if not is_valid_logo_location(logo_path):
            console.print(
                f"[yellow]Warning: Invalid logo location; will fall back to the saved/built-in default if available: {logo_path}[/yellow]"
            )

        advanced_branding = Confirm.ask("\n[dim]Configure advanced logo settings (position, scale)?[/dim]", default=False)
        if advanced_branding:
            logo_position = Prompt.ask(
                "Logo position",
                choices=["top-right", "top-left", "bottom-right", "bottom-left"],
                default=logo_position,
            )
            logo_scale_str = Prompt.ask("Logo scale (e.g., 0.1)", default=str(logo_scale))
            try:
                logo_scale = float(logo_scale_str)
            except ValueError:
                console.print(f"[yellow]Invalid scale, using default: {logo_scale}[/yellow]")

        if Confirm.ask("[dim]Set this logo as the default for future exports?[/dim]", default=False):
            if is_valid_logo_location(logo_path):
                state_manager.set_setting("logo_path", normalize_logo_setting_value(logo_path))
            else:
                console.print(f"[yellow]Warning: Invalid logo location; default not updated: {logo_path}[/yellow]")

    resolved_logo_path = resolve_logo_path(
        user_logo_path=logo_path if add_logo else None,
        saved_logo_path=saved_logo_path,
        builtin_logo_path=DEFAULT_BUILTIN_LOGO_PATH,
    )
    if add_logo and not resolved_logo_path:
        console.print("[yellow]Warning: No valid logo found; continuing without logo overlay.[/yellow]")
        add_logo = False

    console.print()
    add_subtitles = Confirm.ask("[cyan]Add burned-in subtitles (English)?[/cyan]", default=True)
    subtitle_style = "small"
    if add_subtitles:
        console.print()
        style_options = Table(show_header=False, box=None, padding=(0, 2))
        style_options.add_column(style="cyan")
        style_options.add_column(style="white")
        style_options.add_column(style="dim")
        style_options.add_row("1", "Default (18px)", "White text, medium size")
        style_options.add_row("2", "Bold (22px)", "Bold white text")
        style_options.add_row("3", "Yellow (20px)", "Yellow text (classic)")
        style_options.add_row("4", "TikTok (20px)", "Centered top")
        style_options.add_row("5", "Small (10px)", "Very small, positioned higher")
        style_options.add_row("6", "Tiny (8px)", "Extra tiny, positioned higher")
        console.print(style_options)
        console.print()
        style_choice = Prompt.ask("[cyan]Subtitle style[/cyan]", choices=["1", "2", "3", "4", "5", "6"], default="5")
        style_map = {"1": "default", "2": "bold", "3": "yellow", "4": "tiktok", "5": "small", "6": "tiny"}
        subtitle_style = style_map[style_choice]

    console.print()
    organize_by_style = Confirm.ask(
        "[cyan]Organize by style when classifications exist?[/cyan]",
        default=True
    )

    console.print()
    export_all = Confirm.ask("[cyan]Export all clips per video?[/cyan]", default=True)
    max_per_video = None
    if not export_all:
        max_per_video = int(Prompt.ask("[cyan]How many clips per video?[/cyan]", default="10"))

    console.print()
    if not Confirm.ask(f"[cyan]Start export for {len(selected)} video(s)?[/cyan]", default=True):
        console.print("[yellow]Export cancelled[/yellow]")
        return

    exporter = VideoExporter(output_dir="output")

    ok = 0
    skipped = 0
    failed = 0
    for video in selected:
        video_id = video["video_id"]
        state = state_manager.get_video_state(video_id) or {}

        if not state.get("clips_generated"):
            skipped += 1
            console.print(f"[yellow]Skipping (no clips): {video['filename']}[/yellow]")
            continue

        clips = state.get("clips") or []
        if not clips:
            skipped += 1
            console.print(f"[yellow]Skipping (empty clips list): {video['filename']}[/yellow]")
            continue

        clips_to_export = clips if max_per_video is None else clips[:max_per_video]

        transcript_path = state.get("transcript_path") or state.get("transcription_path")
        if add_subtitles and (not transcript_path or not Path(transcript_path).exists()):
            skipped += 1
            console.print(f"[yellow]Skipping (missing transcript for subtitles): {video['filename']}[/yellow]")
            continue

        clip_styles = _load_clip_styles_if_present(video_id) if organize_by_style else None

        try:
            console.print(f"\n[cyan]Exporting clips: {video['filename']}[/cyan]")
            exported_paths = exporter.export_clips(
                video_path=video["path"],
                clips=clips_to_export,
                aspect_ratio=aspect_ratio,
                video_name=video_id,
                add_subtitles=add_subtitles,
                transcript_path=transcript_path,
                subtitle_style=subtitle_style,
                organize_by_style=organize_by_style and bool(clip_styles),
                clip_styles=clip_styles,
                enable_face_tracking=enable_face_tracking,
                face_tracking_strategy=face_tracking_strategy,
                face_tracking_sample_rate=face_tracking_sample_rate,
                add_logo=add_logo,
                logo_path=resolved_logo_path,
                logo_position=logo_position,
                logo_scale=logo_scale
            )
            if exported_paths:
                state_manager.mark_clips_exported(video_id, exported_paths, aspect_ratio=aspect_ratio)
                ok += 1
            else:
                failed += 1
        except KeyboardInterrupt:
            raise
        except Exception as e:
            failed += 1
            console.print(f"[red]Failed: {video['filename']} → {e}[/red]")

    console.print()
    console.print(Panel(
        f"[green]Done[/green]\n\n"
        f"Exported: {ok}\n"
        f"Skipped: {skipped}\n"
        f"Failed: {failed}",
        border_style="green" if failed == 0 else "yellow"
    ))

    console.print()
    Prompt.ask("[dim]Press ENTER to return[/dim]", default="")


def opcion_transcribir_video(video: Dict, state_manager):
    """
    Transcribo un video usando WhisperX

    Este es el paso clave que convierte el audio en texto con timestamps.
    Estos timestamps me permiten después detectar dónde cortar los clips.
    """
    console.clear()
    mostrar_banner()

    video_path = video['path']
    video_id = video['video_id']

    # Obtengo el preset si existe
    state = state_manager.get_video_state(video_id)
    preset = state.get('preset', {}) if state else {}
    content_type = state.get('content_type', 'tutorial') if state else 'tutorial'

    # Si no hay preset guardado, cargo el default
    if not preset:
        preset = get_preset(content_type)

    transcription_config = preset.get('transcription', {})
    suggested_model = transcription_config.get('model_size', 'base')

    console.print(Panel(
        f"[bold]Transcribe Video[/bold]\n\n"
        f"Video: {video['filename']}\n"
        f"Content Type: {content_type.title()}\n"
        f"Using: WhisperX (optimized for Apple Silicon)",
        border_style="cyan"
    ))
    console.print()

    # Pregunto por la configuración (con sugerencia del preset)
    console.print("[bold]Transcription Settings:[/bold]")
    console.print(f"[dim]Suggested for {content_type}: {suggested_model}[/dim]\n")

    # Selección de modelo
    model_options = Table(show_header=False, box=None, padding=(0, 2))
    model_options.add_column(style="cyan")
    model_options.add_column(style="white")
    model_options.add_column(style="dim")

    model_options.add_row("\\[t]iny", "Fastest", "~1min for 1hr video")
    model_options.add_row("\\[b]ase", "Balanced", "~5min for 1hr video")
    model_options.add_row("\\[s]mall", "Accurate", "~10min for 1hr video")
    model_options.add_row("\\[m]edium", "Very accurate", "~20min for 1hr video")

    console.print(model_options)
    console.print()

    # Shortcut mapping for model selection
    shortcut_map = {"t": "tiny", "b": "base", "s": "small", "m": "medium"}
    valid_inputs = ["tiny", "base", "small", "medium", "t", "b", "s", "m"]

    model_input = Prompt.ask(
        "[cyan]Model size[/cyan]",
        choices=valid_inputs,
        default=suggested_model  # Usa el modelo sugerido del preset
    )

    # Convert shortcut to full model name if needed
    model_size = shortcut_map.get(model_input, model_input)

    # Idioma
    console.print()
    language = Prompt.ask(
        "[cyan]Language (or 'auto' to detect)[/cyan]",
        default="auto"
    )

    # Mapeo de nombres comunes a códigos ISO (WhisperX espera códigos ISO)
    LANGUAGE_MAP = {
        "spanish": "es",
        "español": "es",
        "english": "en",
        "inglés": "en",
        "portuguese": "pt",
        "português": "pt",
        "french": "fr",
        "francés": "fr",
        "german": "de",
        "alemán": "de",
        "italian": "it",
        "italiano": "it",
        "auto": None
    }

    # Normalizar idioma
    lang_lower = language.lower().strip()
    if lang_lower in LANGUAGE_MAP:
        language = LANGUAGE_MAP[lang_lower]
    elif lang_lower == "auto":
        language = None  # WhisperX auto-detecta

    console.print()
    console.print("[yellow]⚠️  Transcription will take several minutes depending on video length[/yellow]")
    console.print("[dim]You can see the progress in the terminal[/dim]\n")

    if not Confirm.ask("[cyan]Start transcription?[/cyan]", default=True):
        console.print("[yellow]Cancelled[/yellow]")
        Prompt.ask("\n[dim]Press ENTER to return[/dim]", default="")
        return

    try:
        # Creo el transcriber
        console.print("\n[cyan]Loading Whisper model...[/cyan]")
        transcriber = Transcriber(model_size=model_size)

        # Transcribo
        console.print(f"[cyan]Transcribing {video['filename']}...[/cyan]\n")

        transcript_path = transcriber.transcribe(
            video_path=video_path,
            language=language,
            skip_if_exists=False  # Siempre regenero si el usuario lo pidió
        )

        if transcript_path:
            # Actualizo el estado
            state_manager.mark_transcribed(video_id, transcript_path)

            # Obtengo resumen de la transcripción
            summary = transcriber.get_transcript_summary(transcript_path)

            console.print()
            console.print(Panel(
                f"[green]✓ Transcription completed![/green]\n\n"
                f"Language: {summary['language']}\n"
                f"Duration: {summary['total_duration']:.1f} seconds\n"
                f"Segments: {summary['num_segments']}\n"
                f"Words: {summary['total_words']}\n\n"
                f"Saved to: {transcript_path}",
                title="[bold green]Success[/bold green]",
                border_style="green"
            ))

            console.print()
            console.print("[dim]Preview:[/dim]")
            console.print(f"[dim]{summary['first_text']}[/dim]")

        else:
            console.print(Panel(
                "[red]Transcription failed. Check the logs above.[/red]",
                border_style="red"
            ))

    except KeyboardInterrupt:
        console.print("\n[yellow]Transcription cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")

    console.print()
    Prompt.ask("[dim]Press ENTER to return to menu[/dim]", default="")


def opcion_generar_clips(video: Dict, state_manager):
    """
    Genero clips automáticamente detectando cambios de tema

    Este es el paso donde ClipsAI analiza la transcripción y detecta
    los mejores puntos de corte para crear clips virales.
    """
    console.clear()
    mostrar_banner()

    video_path = video['path']
    video_id = video['video_id']

    # Verifico que tenga transcripción
    state = state_manager.get_video_state(video_id)

    if not state or not state.get('transcribed'):
        console.print(Panel(
            "[red]Error: This video hasn't been transcribed yet[/red]\n\n"
            "You need to transcribe the video first before generating clips.",
            border_style="red"
        ))
        Prompt.ask("\n[dim]Press ENTER to return[/dim]", default="")
        return

    transcript_path = state.get('transcript_path') or state.get('transcription_path')

    # Obtengo el preset para clips
    preset = state.get('preset', {})
    content_type = state.get('content_type', 'tutorial')

    if not preset:
        preset = get_preset(content_type)

    clips_config = preset.get('clips', {})
    suggested_min = clips_config.get('min_duration', 30)
    suggested_max = clips_config.get('max_duration', 90)

    console.print(Panel(
        f"[bold]Generate Clips[/bold]\n\n"
        f"Video: {video['filename']}\n"
        f"Content Type: {content_type.title()}\n"
        f"Using: ClipsAI (AI-powered clip detection)",
        border_style="cyan"
    ))
    console.print()

    # Pregunto por la configuración (con sugerencia del preset)
    console.print("[bold]Clip Generation Settings:[/bold]")
    console.print(f"[dim]Suggested for {content_type}: {suggested_min}-{suggested_max}s clips[/dim]\n")

    # Determino qué opción corresponde a la sugerencia
    if suggested_max <= 60:
        suggested_choice = "1"
    elif suggested_max <= 90:
        suggested_choice = "2"
    else:
        suggested_choice = "3"

    # Duración de clips
    duration_options = Table(show_header=False, box=None, padding=(0, 2))
    duration_options.add_column(style="cyan")
    duration_options.add_column(style="white")
    duration_options.add_column(style="dim")

    duration_options.add_row("1", "Short clips", "30-60s (TikTok/Shorts)")
    duration_options.add_row("2", "Medium clips", "30-90s (Reels/Stories)")
    duration_options.add_row("3", "Long clips", "60-180s (YouTube)")
    duration_options.add_row("4", "Custom", f"Use preset: {suggested_min}-{suggested_max}s")

    console.print(duration_options)
    console.print()

    duration_choice = Prompt.ask(
        "[cyan]Clip duration preset[/cyan]",
        choices=["1", "2", "3", "4"],
        default="4"  # Default usa el preset del content type
    )

    # Mapeo de presets
    duration_presets = {
        "1": (30, 60),   # Short
        "2": (30, 90),   # Medium
        "3": (60, 180),  # Long
        "4": (suggested_min, suggested_max)  # Del content type
    }

    min_duration, max_duration = duration_presets[duration_choice]

    # Calculo estimado de clips (basado en la transcripción)
    try:
        import json
        with open(transcript_path, 'r') as f:
            transcript_data = json.load(f)
            segments = transcript_data.get('segments', [])
            if segments:
                total_duration = segments[-1].get('end', 0)
                estimated_clips = int(total_duration / max_duration)

                console.print()
                console.print(f"[dim]Video duration: {total_duration/60:.1f} minutes[/dim]")
                console.print(f"[dim]Estimated clips with {max_duration}s duration: ~{estimated_clips}[/dim]")
    except:
        pass  # Si falla, no es crítico

    # Número de clips
    console.print()
    num_clips = Prompt.ask(
        "[cyan]Maximum number of clips to generate[/cyan]",
        default="100"  # Aumentado para videos largos (livestreams, conferencias)
    )

    try:
        max_clips = int(num_clips)
    except ValueError:
        max_clips = 10

    console.print()
    console.print("[yellow]⚠️  Clip generation uses AI and may take 1-2 minutes[/yellow]")
    console.print("[dim]ClipsAI will analyze the transcript and detect topic changes[/dim]\n")

    if not Confirm.ask("[cyan]Start clip generation?[/cyan]", default=True):
        console.print("[yellow]Cancelled[/yellow]")
        Prompt.ask("\n[dim]Press ENTER to return[/dim]", default="")
        return

    try:
        # Creo el generador de clips
        console.print("\n[cyan]Initializing ClipsAI...[/cyan]")
        clips_gen = ClipsGenerator(
            min_clip_duration=min_duration,
            max_clip_duration=max_duration
        )

        # Genero los clips
        console.print(f"[cyan]Analyzing transcript and detecting clips...[/cyan]\n")

        clips = clips_gen.generate_clips(
            transcript_path=transcript_path,
            min_clips=3,
            max_clips=max_clips
        )

        if clips:
            # Guardo la metadata de los clips
            clips_metadata_path = clips_gen.save_clips_metadata(
                clips=clips,
                video_id=video_id
            )

            # Actualizo el estado
            state_manager.mark_clips_generated(video_id, clips, clips_metadata_path)

            console.print()
            console.print(Panel(
                f"[green]✓ Clips generated successfully![/green]\n\n"
                f"Number of clips: {len(clips)}\n"
                f"Duration range: {min_duration}s - {max_duration}s\n\n"
                f"Metadata saved to: {clips_metadata_path}",
                title="[bold green]Success[/bold green]",
                border_style="green"
            ))

            # Muestro preview de los clips
            console.print()
            console.print("[bold]Generated Clips:[/bold]\n")

            clips_table = Table(
                show_header=True,
                header_style="bold cyan",
                box=box.ROUNDED,
                border_style="cyan"
            )

            clips_table.add_column("#", style="cyan", width=4)
            clips_table.add_column("Duration", style="white", width=10)
            clips_table.add_column("Time Range", style="dim", width=15)
            clips_table.add_column("Preview", style="white")

            for clip in clips[:10]:  # Muestro máximo 10 en la tabla
                clip_id = clip['clip_id']
                duration = f"{clip['duration']:.1f}s"
                start = clip['start_time']
                end = clip['end_time']
                time_range = f"{int(start//60):02d}:{int(start%60):02d} - {int(end//60):02d}:{int(end%60):02d}"

                # Preview (trunco si es muy largo)
                preview = clip['text_preview']
                if len(preview) > 50:
                    preview = preview[:47] + "..."

                clips_table.add_row(
                    str(clip_id),
                    duration,
                    time_range,
                    preview
                )

            console.print(clips_table)

            if len(clips) > 10:
                console.print(f"\n[dim]... and {len(clips) - 10} more clips[/dim]")

        else:
            console.print(Panel(
                "[red]Clip generation failed[/red]\n\n"
                "Possible reasons:\n"
                "• Video too short for specified duration range\n"
                "• No clear topic changes detected\n"
                "• Try adjusting min/max duration settings",
                border_style="red"
            ))

    except KeyboardInterrupt:
        console.print("\n[yellow]Clip generation cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        console.print("[dim]Check the logs for more details[/dim]")

    console.print()
    Prompt.ask("[dim]Press ENTER to return to menu[/dim]", default="")


def opcion_generar_copies(video: Dict, state_manager):
    """
    Genero copies automáticamente usando LangGraph + Gemini

    Este paso clasifica cada clip automáticamente (viral/educational/storytelling)
    y genera el caption optimizado para cada uno usando AI.
    """
    console.clear()
    mostrar_banner()

    video_id = video['video_id']

    # Verifico que tenga clips generados
    state = state_manager.get_video_state(video_id)

    if not state or not state.get('clips_generated'):
        console.print(Panel(
            "[red]Error: This video doesn't have clips yet[/red]\n\n"
            "You need to generate clips first before creating AI copies.",
            border_style="red"
        ))
        Prompt.ask("\n[dim]Press ENTER to return[/dim]", default="")
        return

    clips = state.get('clips', [])

    console.print(Panel(
        f"[bold]Generate AI Copies[/bold]\n\n"
        f"Video: {video['filename']}\n"
        f"Clips: {len(clips)}\n\n"
        f"This will:\n"
        f"  1. Auto-classify each clip (viral/educational/storytelling)\n"
        f"  2. Generate optimized captions with hashtags\n"
        f"  3. Save to output/{video_id}/copys/clips_copys.json",
        border_style="cyan"
    ))
    console.print()

    # Selección de modelo
    console.print("[bold]Model Selection:[/bold]\n")

    model_table = Table(show_header=False, box=None, padding=(0, 2))
    model_table.add_column(style="cyan")
    model_table.add_column(style="white")
    model_table.add_column(style="dim")

    model_table.add_row("1", "Gemini 2.5 Flash", "Your model (recommended)")
    model_table.add_row("2", "Gemini 1.5 Pro", "Alternative")

    console.print(model_table)
    console.print()

    model_choice = Prompt.ask(
        "[cyan]Choose model[/cyan]",
        choices=["1", "2"],
        default="1"
    )

    # Intentar diferentes nombres de modelo para Gemini 2.5 Flash
    model_map = {
        "1": "gemini-2.5-flash",  # Nombre probable
        "2": "gemini-1.5-pro"
    }

    model = model_map[model_choice]

    console.print()
    console.print("[yellow]⚠️  This will use Gemini API (requires GOOGLE_API_KEY)[/yellow]")
    console.print(f"[dim]Estimated time: ~1-2 minutes for {len(clips)} clips[/dim]\n")

    if not Confirm.ask("[cyan]Start AI copy generation?[/cyan]", default=True):
        console.print("[yellow]Cancelled[/yellow]")
        Prompt.ask("\n[dim]Press ENTER to return[/dim]", default="")
        return

    try:
        console.print()
        console.print("[cyan]Generating AI copies...[/cyan]\n")

        # Generar copies
        result = generate_copys_for_video(
            video_id=video_id,
            model=model
        )

        # Mostrar todos los logs primero
        if result.get('logs'):
            console.print()
            console.print("[bold]Process logs:[/bold]")
            for log in result['logs']:
                if '❌' in log or 'Error' in log:
                    console.print(f"[red]{log}[/red]")
                elif '⚠️' in log:
                    console.print(f"[yellow]{log}[/yellow]")
                elif '✅' in log:
                    console.print(f"[green]{log}[/green]")
                else:
                    console.print(f"[dim]{log}[/dim]")

        console.print()

        if result['success']:
            # Determinar si es éxito total o parcial
            total_generated = result['metrics']['total_copies']
            total_classified = result['metrics'].get('total_classified', total_generated)
            is_partial = total_generated < total_classified

            if is_partial:
                title_text = "[bold yellow]Partial Success[/bold yellow]"
                border_color = "yellow"
                status_line = f"[yellow]⚠️  Generación parcial: {total_generated}/{total_classified} copies[/yellow]"
            else:
                title_text = "[bold green]Success[/bold green]"
                border_color = "green"
                status_line = f"[green]✓ AI copies generated successfully![/green]"

            console.print(Panel(
                f"{status_line}\n\n"
                f"Total copies: {total_generated}\n"
                f"Engagement score: {result['metrics']['average_engagement']}/10\n"
                f"Viral potential: {result['metrics']['average_viral_potential']}/10\n\n"
                f"Distribution:\n"
                f"  • Viral: {result['metrics']['distribution']['viral']} clips\n"
                f"  • Educational: {result['metrics']['distribution']['educational']} clips\n"
                f"  • Storytelling: {result['metrics']['distribution']['storytelling']} clips\n\n"
                f"Saved to: {result['output_file']}",
                title=title_text,
                border_style=border_color
            ))

        else:
            console.print(Panel(
                f"[red]Copy generation failed[/red]\n\n"
                f"Error: {result.get('error', 'Unknown error')}\n\n"
                f"Check the logs above for details.\n\n"
                f"Possible causes:\n"
                f"• GOOGLE_API_KEY not set\n"
                f"• Model not available with your API key\n"
                f"• API quota exceeded\n"
                f"• Network issues",
                border_style="red"
            ))

    except KeyboardInterrupt:
        console.print("\n[yellow]Copy generation cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        console.print("[dim]Check that GOOGLE_API_KEY is set in your environment[/dim]")

    console.print()
    Prompt.ask("[dim]Press ENTER to return to menu[/dim]", default="")


def opcion_exportar_clips(video: Dict, state_manager):
    """
    Exporto los clips a archivos de video físicos usando ffmpeg

    Este es el paso final donde convirtiendo los timestamps en videos reales.
    Puedo exportar con diferentes aspect ratios para redes sociales.

    Si existen clasificaciones (clips_copys.json), pregunta si organizar por estilo.
    """
    console.clear()
    mostrar_banner()

    video_path = video['path']
    video_id = video['video_id']

    # Verifico que tenga clips generados
    state = state_manager.get_video_state(video_id)

    if not state or not state.get('clips_generated'):
        console.print(Panel(
            "[red]Error: This video doesn't have clips yet[/red]\n\n"
            "You need to generate clips first before exporting.",
            border_style="red"
        ))
        Prompt.ask("\n[dim]Press ENTER to return[/dim]", default="")
        return

    clips = state.get('clips', [])

    if not clips:
        console.print(Panel(
            "[red]Error: No clips found[/red]",
            border_style="red"
        ))
        Prompt.ask("\n[dim]Press ENTER to return[/dim]", default="")
        return

    # Verificar si existen clasificaciones
    copys_file = Path("output") / video_id / "copys" / "clips_copys.json"
    has_classifications = copys_file.exists()
    clip_styles = None
    organize_by_style = False

    if has_classifications:
        # Cargar clasificaciones
        try:
            import json
            with open(copys_file, 'r', encoding='utf-8') as f:
                copys_data = json.load(f)

            # Extraer clasificaciones de clips
            classifications = copys_data.get('classification_metadata', {}).get('classifications', [])

            if classifications:
                clip_styles = {c['clip_id']: c['style'] for c in classifications}

                # Mostrar distribución
                distribution = copys_data.get('classification_metadata', {}).get('distribution', {})
                viral_count = distribution.get('viral', 0)
                educational_count = distribution.get('educational', 0)
                storytelling_count = distribution.get('storytelling', 0)

                console.print(Panel(
                    f"[green]✓ Clips already classified![/green]\n\n"
                    f"Distribution:\n"
                    f"  • Viral: {viral_count} clips\n"
                    f"  • Educational: {educational_count} clips\n"
                    f"  • Storytelling: {storytelling_count} clips",
                    title="[bold green]Auto-Classification Detected[/bold green]",
                    border_style="green"
                ))
                console.print()
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load classifications: {e}[/yellow]\n")

    console.print(Panel(
        f"[bold]Export Clips to Video Files[/bold]\n\n"
        f"Video: {video['filename']}\n"
        f"Clips to export: {len(clips)}\n"
        f"Using: ffmpeg (optimized cutting)",
        border_style="cyan"
    ))
    console.print()

    # Pregunto por aspect ratio
    console.print("[bold]Export Settings:[/bold]\n")

    aspect_options = Table(show_header=False, box=None, padding=(0, 2))
    aspect_options.add_column(style="cyan")
    aspect_options.add_column(style="white")
    aspect_options.add_column(style="dim")

    aspect_options.add_row("1", "Original", "Keep video aspect ratio (usually 16:9)")
    aspect_options.add_row("2", "Vertical (9:16)", "For TikTok, Reels, Shorts")
    aspect_options.add_row("3", "Square (1:1)", "For Instagram posts")

    console.print(aspect_options)
    console.print()

    aspect_choice = Prompt.ask(
        "[cyan]Aspect ratio[/cyan]",
        choices=["1", "2", "3"],
        default="2"  # Default: vertical para redes sociales
    )

    # Mapeo de aspect ratios
    aspect_map = {
        "1": None,      # Original
        "2": "9:16",    # Vertical
        "3": "1:1"      # Square
    }

    aspect_ratio = aspect_map[aspect_choice]

    # PASO 3: Face tracking configuration
    enable_face_tracking = False
    face_tracking_strategy = "keep_in_frame"
    face_tracking_sample_rate = 3

    if aspect_ratio == "9:16":  # Solo relevante para videos verticales
        console.print()
        enable_face_tracking = Confirm.ask(
            "[cyan]Enable intelligent face tracking for dynamic reframing?[/cyan]",
            default=False
        )

        if enable_face_tracking:
            console.print("\n[bold]Face Tracking Strategy:[/bold]")
            console.print("  [cyan]1.[/cyan] keep_in_frame (recommended) - Minimal movement, professional look")
            console.print("  [cyan]2.[/cyan] centered - Always center on face (can be jittery)")

            style_choice = Prompt.ask(
                "\n[cyan]Choice[/cyan]",
                choices=["1", "2"],
                default="1"
            )

            face_tracking_strategy = "keep_in_frame" if style_choice == "1" else "centered"

            # Advanced settings (opcional)
            console.print()
            advanced = Confirm.ask(
                "[dim]Configure advanced settings (frame sampling)?[/dim]",
                default=False
            )

            if advanced:
                sample_rate_input = Prompt.ask(
                    "Frame sample rate (process every N frames)",
                    default="3"
                )
                try:
                    face_tracking_sample_rate = int(sample_rate_input)
                except ValueError:
                    console.print("[yellow]Invalid input, using default: 3[/yellow]")
                    face_tracking_sample_rate = 3

            # Visual confirmation
            console.print()
            console.print("[green]✓[/green] Face tracking enabled:")
            console.print(f"  Strategy: [cyan]{face_tracking_strategy}[/cyan]")
            console.print(f"  Sample rate: every [cyan]{face_tracking_sample_rate}[/cyan] frame(s)")

    # --- Branding (Logo Only) ---
    console.print()
    add_logo = Confirm.ask("[cyan]Add logo overlay to clips?[/cyan]", default=False)
    
    saved_logo_path = state_manager.get_setting("logo_path", DEFAULT_BUILTIN_LOGO_PATH)
    logo_path = saved_logo_path
    logo_position = "top-right"
    logo_scale = 0.1

    if add_logo:
        console.print(f"[green]✓[/green] Logo overlay enabled.")
        console.print(f"[dim]Current default logo location:[/dim] {saved_logo_path}")
        logo_path = Prompt.ask("Logo file path (or directory)", default=logo_path)
        if not is_valid_logo_location(logo_path):
            console.print(
                f"[yellow]Warning: Invalid logo location; will fall back to the saved/built-in default if available: {logo_path}[/yellow]"
            )
        
        advanced_branding = Confirm.ask("\n[dim]Configure advanced logo settings (position, scale)?[/dim]", default=False)
        if advanced_branding:
            logo_position = Prompt.ask(
                "Logo position",
                choices=["top-right", "top-left", "bottom-right", "bottom-left"],
                default=logo_position
            )
            logo_scale_str = Prompt.ask("Logo scale (e.g., 0.1 for 10% of height)", default=str(logo_scale))
            try:
                logo_scale = float(logo_scale_str)
            except ValueError:
                console.print(f"[yellow]Invalid scale, using default: {logo_scale}[/yellow]")

        if Confirm.ask("[dim]Set this logo as the default for future exports?[/dim]", default=False):
            if is_valid_logo_location(logo_path):
                state_manager.set_setting("logo_path", normalize_logo_setting_value(logo_path))
            else:
                console.print(f"[yellow]Warning: Invalid logo location; default not updated: {logo_path}[/yellow]")

    resolved_logo_path = resolve_logo_path(
        user_logo_path=logo_path if add_logo else None,
        saved_logo_path=saved_logo_path,
        builtin_logo_path=DEFAULT_BUILTIN_LOGO_PATH,
    )
    if add_logo and not resolved_logo_path:
        console.print("[yellow]Warning: No valid logo found; continuing without logo overlay.[/yellow]")
        add_logo = False

    # Pregunto si quiere subtítulos
    console.print()
    add_subtitles = Confirm.ask(
        "[cyan]Add burned-in subtitles (English)?[/cyan]",
        default=True
    )

    subtitle_style = "default"
    if add_subtitles:
        console.print()
        console.print("[bold]Subtitle Style:[/bold]\n")

        style_options = Table(show_header=False, box=None, padding=(0, 2))
        style_options.add_column(style="cyan")
        style_options.add_column(style="white")
        style_options.add_column(style="dim")

        style_options.add_row("1", "Default (18px)", "White text, medium size")
        style_options.add_row("2", "Bold (22px)", "Bold white text")
        style_options.add_row("3", "Yellow (20px)", "Yellow text (classic)")
        style_options.add_row("4", "TikTok (20px)", "Centered top")
        style_options.add_row("5", "Small (10px)", "Very small, positioned higher")
        style_options.add_row("6", "Tiny (8px)", "Extra tiny, positioned higher")

        console.print(style_options)
        console.print()

        style_choice = Prompt.ask(
            "[cyan]Subtitle style[/cyan]",
            choices=["1", "2", "3", "4", "5", "6"],
            default="5"  # Default a Small ahora
        )

        style_map = {
            "1": "default",
            "2": "bold",
            "3": "yellow",
            "4": "tiktok",
            "5": "small",
            "6": "tiny"
        }

        subtitle_style = style_map[style_choice]

    # Pregunto si quiere organizar por estilo (si hay clasificaciones)
    if clip_styles:
        console.print()
        organize_by_style = Confirm.ask(
            "[cyan]Organize clips by style in separate folders? (viral/educational/storytelling)[/cyan]",
            default=True
        )

        if organize_by_style:
            console.print("[green]✓ Clips will be organized in subfolders by style[/green]")
        else:
            console.print("[dim]All clips will be exported to the same folder[/dim]")

    # Pregunto si quiere exportar todos o solo algunos
    console.print()
    export_all = Confirm.ask(
        f"[cyan]Export all {len(clips)} clips?[/cyan]",
        default=True
    )

    clips_to_export = clips

    if not export_all:
        console.print()
        max_clips = Prompt.ask(
            "[cyan]How many clips to export (from the beginning)?[/cyan]",
            default="10"
        )
        try:
            clips_to_export = clips[:int(max_clips)]
        except ValueError:
            clips_to_export = clips[:10]

    # Confirmo antes de exportar
    console.print()
    console.print(f"[yellow]⚠️  About to export {len(clips_to_export)} clips[/yellow]")
    console.print(f"[dim]This may take a few minutes depending on video length[/dim]")
    console.print()

    if not Confirm.ask("[cyan]Continue with export?[/cyan]", default=True):
        console.print("[yellow]Export cancelled[/yellow]")
        Prompt.ask("\n[dim]Press ENTER to return[/dim]", default="")
        return

    try:
        console.print()

        # Creo el exporter
        exporter = VideoExporter(output_dir="output")

        # Obtengo el path de la transcripción para los subtítulos
        transcript_path = state.get('transcript_path') or state.get('transcription_path')

        # Mensaje informativo sobre el proceso de export
        if enable_face_tracking:
            console.print("[cyan]Starting export with AI-powered face tracking...[/cyan]")
            console.print("[dim]Note: Face detection may take longer than static crop[/dim]\n")
        else:
            console.print("[cyan]Starting export...[/cyan]\n")

        # Exporto los clips
        exported_paths = exporter.export_clips(
            video_path=video_path,
            clips=clips_to_export,
            aspect_ratio=aspect_ratio,
            video_name=video_id,
            add_subtitles=add_subtitles,
            transcript_path=transcript_path,
            subtitle_style=subtitle_style,
            organize_by_style=organize_by_style,
            clip_styles=clip_styles,
            # PASO 3: Face tracking parameters
            enable_face_tracking=enable_face_tracking,
            face_tracking_strategy=face_tracking_strategy,
            face_tracking_sample_rate=face_tracking_sample_rate,
            # PASO 4: Branding parameters
            add_logo=add_logo,
            logo_path=resolved_logo_path,
            logo_position=logo_position,
            logo_scale=logo_scale
        )

        if exported_paths:
            # Obtengo la carpeta donde se guardaron (todos están en la misma)
            output_folder = Path(exported_paths[0]).parent

            console.print()
            console.print(Panel(
                f"[green]✓ Export completed![/green]\n\n"
                f"Clips exported: {len(exported_paths)}\n"
                f"Location: {output_folder}/\n"
                f"Aspect ratio: {aspect_ratio if aspect_ratio else 'Original'}",
                title="[bold green]Success[/bold green]",
                border_style="green"
            ))

            # Muestro algunos nombres de archivo
            console.print()
            console.print("[dim]Sample clips:[/dim]")
            for path in exported_paths[:5]:
                filename = Path(path).name
                console.print(f"[dim]  • {filename}[/dim]")

            if len(exported_paths) > 5:
                console.print(f"[dim]  ... and {len(exported_paths) - 5} more[/dim]")

            # Marco como exportado en el state manager
            state_manager.mark_clips_exported(
                video_id,
                exported_paths,
                aspect_ratio=aspect_ratio
            )

        else:
            console.print(Panel(
                "[red]Export failed[/red]\n\n"
                "Check the logs for details about what went wrong.",
                border_style="red"
            ))

    except KeyboardInterrupt:
        console.print("\n[yellow]Export cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        console.print("[dim]Check the logs for more details[/dim]")

    console.print()
    Prompt.ask("[dim]Press ENTER to return to menu[/dim]", default="")


def opcion_cleanup_project():
    """
    Flujo interactivo para limpiar artifacts del proyecto

    DECISIÓN: Interactivo con confirmación obligatoria
    RAZÓN: Operación destructiva - prevenir eliminaciones accidentales
    """
    console.clear()
    mostrar_banner()

    console.print(Panel(
        "[bold]Cleanup Project Data[/bold]\nManage and delete project artifacts",
        border_style="cyan"
    ))
    console.print()

    cleanup_manager = CleanupManager()
    state_manager = get_state_manager()
    state = state_manager.get_all_videos()

    if not state:
        console.print("[yellow]No project data to clean (state is empty)[/yellow]")
        console.print()
        Prompt.ask("[dim]Press ENTER to return to menu[/dim]", default="")
        return

    # Mostrar artifacts disponibles
    console.print("[bold]Cleanable Project Data:[/bold]\n")
    cleanup_manager.display_cleanable_artifacts()
    console.print()

    # Opciones de cleanup
    menu_table = Table(show_header=False, box=box.ROUNDED, border_style="cyan", padding=(0, 2))
    menu_table.add_column("Option", style="bold cyan", width=8)
    menu_table.add_column("Description", style="white")

    menu_table.add_row("1", "Clean specific video")
    menu_table.add_row("2", "Clean all outputs only (keep transcripts)")
    menu_table.add_row("3", "Clean entire project (fresh start)")
    menu_table.add_row("4", "Back to main menu")

    console.print(Panel(menu_table, title="[bold]Cleanup Options[/bold]", border_style="cyan"))
    console.print()

    choice = Prompt.ask(
        "[bold cyan]Choose cleanup option[/bold cyan]",
        choices=["1", "2", "3", "4"],
        default="4"
    )

    if choice == "1":
        cleanup_specific_video(cleanup_manager, state)
    elif choice == "2":
        cleanup_outputs_only(cleanup_manager, state)
    elif choice == "3":
        cleanup_entire_project(cleanup_manager)
    elif choice == "4":
        return

    console.print()
    Prompt.ask("[dim]Press ENTER to return to menu[/dim]", default="")


def cleanup_specific_video(cleanup_manager: CleanupManager, state: dict):
    """Cleanup de un video específico con selección granular"""
    console.print()

    # Listar videos disponibles
    video_keys = list(state.keys())

    console.print("[bold]Available videos:[/bold]\n")

    videos_table = Table(show_header=False, box=None, padding=(0, 2))
    videos_table.add_column(style="cyan", width=6)
    videos_table.add_column(style="white")

    for idx, video_key in enumerate(video_keys, 1):
        # Nombre corto del video
        video_name = video_key[:50] + "..." if len(video_key) > 50 else video_key
        videos_table.add_row(str(idx), video_name)

    videos_table.add_row(str(len(video_keys) + 1), "[dim]Cancel[/dim]")

    console.print(videos_table)
    console.print()

    video_idx = Prompt.ask(
        "[cyan]Select video to clean[/cyan]",
        choices=[str(i) for i in range(1, len(video_keys) + 2)],
        default=str(len(video_keys) + 1)
    )

    if int(video_idx) == len(video_keys) + 1:
        console.print("[yellow]Cleanup cancelled[/yellow]")
        return

    selected_video_key = video_keys[int(video_idx) - 1]

    # Mostrar artifacts de ese video
    artifacts = cleanup_manager.get_video_artifacts(selected_video_key)

    console.print(f"\n[bold]Artifacts for '{selected_video_key[:50]}':[/bold]\n")

    artifact_options = []
    for artifact_type, info in artifacts.items():
        if info['exists']:
            size_mb = info['size'] / 1024 / 1024
            console.print(f"  - {artifact_type}: {size_mb:.2f} MB")
            artifact_options.append(artifact_type)

    if not artifact_options:
        console.print("[yellow]No artifacts to clean for this video[/yellow]")
        return

    # Selección granular
    console.print()
    menu_table = Table(show_header=False, box=None, padding=(0, 2))
    menu_table.add_column(style="cyan", width=6)
    menu_table.add_column(style="white")

    menu_table.add_row("1", "All artifacts")
    menu_table.add_row("2", "Select specific artifacts")
    menu_table.add_row("3", "Cancel")

    console.print(menu_table)
    console.print()

    granular_choice = Prompt.ask(
        "[cyan]What to clean?[/cyan]",
        choices=["1", "2", "3"],
        default="3"
    )

    if granular_choice == "3":
        console.print("[yellow]Cleanup cancelled[/yellow]")
        return

    if granular_choice == "1":
        to_delete = artifact_options
    else:
        # Selección manual
        console.print()
        to_delete = []
        for artifact_type in artifact_options:
            delete_it = Confirm.ask(f"Delete {artifact_type}?", default=False)
            if delete_it:
                to_delete.append(artifact_type)

    if not to_delete:
        console.print("[yellow]Nothing selected to delete[/yellow]")
        return

    # Calcular total a eliminar
    total_size = sum(
        artifacts[t]['size']
        for t in to_delete
        if t in artifacts
    )
    total_mb = total_size / 1024 / 1024

    # CONFIRMACIÓN FINAL
    console.print(f"\n[bold red]This will DELETE {len(to_delete)} items ({total_mb:.2f} MB)[/bold red]")
    for t in to_delete:
        console.print(f"  - {t}")
    console.print()

    if not Confirm.ask("Continue?", default=False):
        console.print("[yellow]Cleanup cancelled[/yellow]")
        return

    # Ejecutar cleanup
    console.print("\n[bold]Cleaning...[/bold]")
    results = cleanup_manager.delete_video_artifacts(selected_video_key, to_delete)

    # Mostrar resultados
    success_count = sum(1 for r in results.values() if r)
    console.print(f"\n[green]Deleted {success_count}/{len(to_delete)} items ({total_mb:.2f} MB freed)[/green]")


def cleanup_outputs_only(cleanup_manager: CleanupManager, state: dict):
    """Elimina SOLO los outputs exportados (conserva transcripts)"""
    console.print()

    # Calcular total de outputs
    total_output_size = 0
    total_clips = 0

    for video_key in state.keys():
        artifacts = cleanup_manager.get_video_artifacts(video_key)
        output_info = artifacts.get('output', {})

        if output_info.get('exists'):
            total_output_size += output_info.get('size', 0)
            total_clips += output_info.get('clip_count', 0)

    if total_output_size == 0:
        console.print("[yellow]No exported clips to clean[/yellow]")
        return

    size_mb = total_output_size / 1024 / 1024

    console.print("[bold]This will delete ALL exported clips:[/bold]")
    console.print(f"  - Videos: {len(state)} videos")
    console.print(f"  - Clips: {total_clips} clips")
    console.print(f"  - Size: {size_mb:.2f} MB")
    console.print("\n[dim]Transcripts and source videos will be preserved[/dim]\n")

    if not Confirm.ask("Continue?", default=False):
        console.print("[yellow]Cleanup cancelled[/yellow]")
        return

    # Eliminar outputs de cada video
    console.print("\n[bold]Cleaning outputs...[/bold]")
    deleted_count = 0
    for video_key in state.keys():
        results = cleanup_manager.delete_video_artifacts(video_key, ['output'])
        if results.get('output'):
            deleted_count += 1

    console.print(f"\n[green]Deleted outputs from {deleted_count} videos ({size_mb:.2f} MB freed)[/green]")


def cleanup_entire_project(cleanup_manager: CleanupManager):
    """Fresh start - elimina TODO el proyecto"""
    console.print()

    console.print("[bold red]WARNING: This will DELETE ALL project data:[/bold red]")
    console.print("  - All downloaded videos")
    console.print("  - All transcripts")
    console.print("  - All detected clips")
    console.print("  - All exported clips")
    console.print("  - Project state\n")

    # Confirmación EXTREMA - requiere escribir "DELETE ALL"
    confirmation = Prompt.ask(
        "[bold]Type 'DELETE ALL' to confirm[/bold]",
        default="cancel"
    )

    if confirmation != "DELETE ALL":
        console.print("[yellow]Cleanup cancelled[/yellow]")
        return

    console.print("\n[bold]Cleaning entire project...[/bold]")

    results = cleanup_manager.delete_all_project_data()

    if all(results.values()):
        console.print("\n[green]Project cleaned successfully[/green]")
        console.print("[dim]Fresh start ready. Run CLIPER to begin.[/dim]")
    else:
        console.print("\n[yellow]Some items could not be deleted[/yellow]")
        for item, success in results.items():
            status = "✓" if success else "✗"
            console.print(f"  {status} {item}")


def main():
    """
    Función principal - loop del programa
    """
    mostrar_banner()

    # Inicializo componentes
    console.print("[cyan]Initializing CLIPER...[/cyan]\n")

    try:
        downloader = YoutubeDownloader()
        state_manager = get_state_manager()
        console.print("[green]✓ System ready[/green]\n")
    except Exception as e:
        console.print(Panel(
            f"[red]Initialization error: {e}[/red]",
            border_style="red"
        ))
        sys.exit(1)

    # Cargar videos (downloads/ + rutas externas registradas)
    console.print("[cyan]Loading videos...[/cyan]")
    videos = cargar_videos_disponibles(state_manager)

    if videos:
        console.print(f"[green]Found {len(videos)} video(s)[/green]\n")
    else:
        console.print("[yellow]No videos found[/yellow]\n")

    # Loop principal
    while True:
        opcion = menu_principal(videos, state_manager)

        # Mapeo de opciones (depende de si hay videos)
        if videos:
            if opcion == "1":
                opcion_procesar_video(videos, state_manager)
            elif opcion == "2":
                opcion_procesar_videos_en_lote(videos, state_manager)
                videos = cargar_videos_disponibles(state_manager)
            elif opcion == "3":
                opcion_descargar_video(downloader, state_manager)
                videos = cargar_videos_disponibles(state_manager)
            elif opcion == "4":
                opcion_cleanup_project()
                videos = cargar_videos_disponibles(state_manager)
            elif opcion == "5":
                break
        else:
            if opcion == "1":
                opcion_descargar_video(downloader, state_manager)
                videos = cargar_videos_disponibles(state_manager)
            elif opcion == "2":
                opcion_cleanup_project()
                videos = cargar_videos_disponibles(state_manager)
            elif opcion == "3":
                break

        console.clear()
        mostrar_banner()

    # Despedida
    console.clear()
    mostrar_banner()

    goodbye = Text()
    goodbye.append("\nThank you for using CLIPER!\n", style="bold green")
    goodbye.append("Keep creating amazing content\n", style="dim")
    goodbye.justify = "center"

    console.print(Panel(
        goodbye,
        title="[bold]Goodbye![/bold]",
        border_style="cyan"
    ))
    console.print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Program interrupted. Goodbye![/yellow]\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
        console.print("[dim]Check the logs for more details[/dim]\n")
        sys.exit(1)
