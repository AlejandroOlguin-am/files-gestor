from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .report import append_organize_csv_row, ensure_reports_dir, write_organize_csv_header
from .rules import DOC_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, OrganizeConfig
from .scan import FileEntry, iter_files_in_dir, list_recup_dirs


@dataclass
class OrganizeStats:
    scanned: int = 0
    copied: int = 0
    moved: int = 0
    skipped: int = 0
    errors: int = 0
    bytes_transferred: int = 0


_MONTH_NAMES = {
    1: "01_enero",
    2: "02_febrero",
    3: "03_marzo",
    4: "04_abril",
    5: "05_mayo",
    6: "06_junio",
    7: "07_julio",
    8: "08_agosto",
    9: "09_septiembre",
    10: "10_octubre",
    11: "11_noviembre",
    12: "12_diciembre",
}


def _find_ffprobe() -> str:
    """Busca ffprobe: primero imageio-ffmpeg, luego el sistema."""
    try:
        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        ffprobe_path = ffmpeg_path.replace("ffmpeg", "ffprobe")
        if os.path.isfile(ffprobe_path):
            return ffprobe_path
    except ImportError:
        pass

    ffprobe_sys = shutil.which("ffprobe")
    if ffprobe_sys:
        return ffprobe_sys

    raise FileNotFoundError(
        "No se encontró ffprobe. Instala 'imageio-ffmpeg' (pip install imageio-ffmpeg) "
        "o instala FFmpeg en tu sistema."
    )


def _get_image_date(entry: FileEntry) -> Optional[datetime]:
    """Lee fecha EXIF de una imagen (tags 36867 → 36868 → 306)."""
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        with Image.open(entry.path) as img:
            exif_data = img._getexif()  # type: ignore[attr-defined]
            if exif_data is None:
                return None

        for tag_id in (36867, 36868, 306):
            raw = exif_data.get(tag_id)
            if raw:
                try:
                    return datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    continue
    except Exception:
        pass
    return None


def _get_video_date(entry: FileEntry, ffprobe_path: str) -> Optional[datetime]:
    """Lee creation_time de los tags de formato usando ffprobe."""
    try:
        result = subprocess.run(
            [
                ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_entries", "format_tags=creation_time",
                entry.path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        creation_time = data.get("format", {}).get("tags", {}).get("creation_time")
        if not creation_time:
            return None
        # Format: "2023-07-14T15:30:00.000000Z" or similar
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(creation_time, fmt)
            except ValueError:
                continue
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return None


def _get_file_date(entry: FileEntry, ffprobe_path: Optional[str]) -> Optional[datetime]:
    """Dispatch de extracción de fecha según tipo de archivo."""
    if entry.extension in IMAGE_EXTENSIONS:
        return _get_image_date(entry)
    if entry.extension in VIDEO_EXTENSIONS and ffprobe_path:
        return _get_video_date(entry, ffprobe_path)
    return None


def _categorize(extension: str) -> str:
    if extension in IMAGE_EXTENSIONS:
        return "fotos"
    if extension in VIDEO_EXTENSIONS:
        return "videos"
    if extension in DOC_EXTENSIONS:
        return "documentos"
    return "sin_clasificar"


def _month_folder(month: int) -> str:
    return _MONTH_NAMES.get(month, f"{month:02d}")


def _dest_path(output_dir: str, category: str, date: Optional[datetime], filename: str) -> str:
    if category == "sin_clasificar":
        return os.path.join(output_dir, "sin_clasificar", filename)

    if date is None:
        return os.path.join(output_dir, category, "sin_fecha", filename)

    return os.path.join(
        output_dir,
        category,
        str(date.year),
        _month_folder(date.month),
        filename,
    )


def _safe_dest(dest_path: str) -> str:
    """Si dest_path ya existe, agrega sufijo _1, _2, ... hasta encontrar uno libre."""
    if not os.path.exists(dest_path):
        return dest_path

    base, ext = os.path.splitext(dest_path)
    counter = 1
    while True:
        candidate = f"{base}_{counter}{ext}"
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def organize(cfg: OrganizeConfig) -> str:
    """Organiza archivos de recup_dir.* hacia output_dir por tipo y fecha."""
    try:
        ffprobe_path: Optional[str] = _find_ffprobe()
        print(f"Usando ffprobe: {ffprobe_path}")
    except FileNotFoundError:
        ffprobe_path = None
        print("ffprobe no encontrado — videos sin fecha de creación.")

    report_paths = ensure_reports_dir(cfg.root_dir, cfg.reports_dirname, prefix="organize")
    write_organize_csv_header(report_paths.report_csv_path)

    recup_dirs = list_recup_dirs(cfg.root_dir, cfg.process_recup_prefix)
    if not recup_dirs:
        raise FileNotFoundError(
            f"No se encontraron carpetas '{cfg.process_recup_prefix}*' dentro de: {cfg.root_dir}"
        )

    stats = OrganizeStats()
    action_verb = "move" if cfg.move else "copy"

    for recup_dir in recup_dirs:
        if os.path.basename(recup_dir) in cfg.exclude_dirnames:
            continue

        print(f"--- Procesando: {recup_dir} ---")
        dir_count = 0

        for entry in iter_files_in_dir(recup_dir):
            stats.scanned += 1
            dir_count += 1

            category = _categorize(entry.extension)
            date = _get_file_date(entry, ffprobe_path)
            filename = os.path.basename(entry.path)
            dest = _dest_path(cfg.output_dir, category, date, filename)

            date_reason = date.strftime("%Y-%m") if date else "sin_fecha"
            reason = f"{category}/{date_reason}"

            if cfg.dry_run:
                append_organize_csv_row(
                    report_paths.report_csv_path,
                    action=action_verb,
                    dry_run=True,
                    reason=reason,
                    extension=entry.extension,
                    size_bytes=entry.size_bytes,
                    source_path=entry.path,
                    destination_path=dest,
                )
                if cfg.move:
                    stats.moved += 1
                else:
                    stats.copied += 1
                stats.bytes_transferred += entry.size_bytes
                continue

            dest = _safe_dest(dest)
            os.makedirs(os.path.dirname(dest), exist_ok=True)

            try:
                if cfg.move:
                    shutil.move(entry.path, dest)
                    stats.moved += 1
                else:
                    shutil.copy2(entry.path, dest)
                    stats.copied += 1
                stats.bytes_transferred += entry.size_bytes

                append_organize_csv_row(
                    report_paths.report_csv_path,
                    action=action_verb,
                    dry_run=False,
                    reason=reason,
                    extension=entry.extension,
                    size_bytes=entry.size_bytes,
                    source_path=entry.path,
                    destination_path=dest,
                )
            except OSError as exc:
                stats.errors += 1
                append_organize_csv_row(
                    report_paths.report_csv_path,
                    action="error",
                    dry_run=False,
                    reason=str(exc),
                    extension=entry.extension,
                    size_bytes=entry.size_bytes,
                    source_path=entry.path,
                    destination_path=dest,
                )

        print(f"  Procesados en esta carpeta: {dir_count}")

    verb_past = "movidos" if cfg.move else "copiados"
    print("-" * 40)
    print(
        f"Resumen TOTAL: scanned={stats.scanned} "
        f"{verb_past}={stats.moved if cfg.move else stats.copied} "
        f"errors={stats.errors} "
        f"({stats.bytes_transferred / 1_000_000:.1f} MB)"
    )
    print(f"Reporte CSV: {report_paths.report_csv_path}")

    return report_paths.report_csv_path
