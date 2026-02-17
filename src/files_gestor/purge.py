from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .report import append_csv_row, ensure_reports_dir, write_csv_header
from .rules import (
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    PurgeByTypeConfig,
    PurgeShortVideosConfig,
    PurgeSmallImagesConfig,
)
from .scan import FileEntry, iter_files_in_dir, list_recup_dirs


@dataclass
class PurgeStats:
    scanned_files: int = 0
    deleted_files: int = 0
    kept_files: int = 0
    errors: int = 0

    deleted_bytes: int = 0
    kept_bytes: int = 0


def _apply_decision(
    *,
    entry: FileEntry,
    should_delete: bool,
    reason: str,
    dry_run: bool,
    report_csv: str,
    stats_total: PurgeStats,
    stats_dir: PurgeStats,
) -> None:
    """Aplica la decisión de borrar o conservar, actualiza stats y CSV."""
    if should_delete:
        append_csv_row(
            report_csv,
            action="delete",
            dry_run=dry_run,
            reason=reason,
            extension=entry.extension,
            size_bytes=entry.size_bytes,
            file_path=entry.path,
        )

        if dry_run:
            stats_total.deleted_files += 1
            stats_dir.deleted_files += 1
            stats_total.deleted_bytes += entry.size_bytes
            stats_dir.deleted_bytes += entry.size_bytes
            return

        try:
            os.remove(entry.path)
            stats_total.deleted_files += 1
            stats_dir.deleted_files += 1
            stats_total.deleted_bytes += entry.size_bytes
            stats_dir.deleted_bytes += entry.size_bytes
        except OSError:
            stats_total.errors += 1
            stats_dir.errors += 1
        return

    # kept
    append_csv_row(
        report_csv,
        action="keep",
        dry_run=dry_run,
        reason=reason,
        extension=entry.extension,
        size_bytes=entry.size_bytes,
        file_path=entry.path,
    )
    stats_total.kept_files += 1
    stats_dir.kept_files += 1
    stats_total.kept_bytes += entry.size_bytes
    stats_dir.kept_bytes += entry.size_bytes


def _print_summary(stats_dir: PurgeStats, stats_total: PurgeStats, report_csv: str) -> None:
    print(
        "Resumen carpeta: "
        f"scanned={stats_dir.scanned_files} "
        f"delete={stats_dir.deleted_files} "
        f"keep={stats_dir.kept_files} "
        f"errors={stats_dir.errors}"
    )


def _print_total(stats_total: PurgeStats, report_csv: str) -> None:
    print("-" * 40)
    print(
        "Resumen TOTAL: "
        f"scanned={stats_total.scanned_files} "
        f"delete={stats_total.deleted_files} "
        f"keep={stats_total.kept_files} "
        f"errors={stats_total.errors}"
    )
    print(f"Reporte CSV: {report_csv}")


# ── Purge by type ──────────────────────────────────────────────────


def _should_delete_by_type(cfg: PurgeByTypeConfig, ext: str, size_bytes: int) -> Tuple[bool, str]:
    if ext == "":
        if size_bytes < cfg.no_extension_delete_below_bytes:
            return True, f"no_extension_below_{cfg.no_extension_delete_below_bytes}"
        return False, "no_extension_kept"

    if ext in cfg.allowed_extensions:
        return False, "allowed_extension"

    return True, "extension_not_allowed"


def purge_by_type(cfg: PurgeByTypeConfig) -> str:
    report_paths = ensure_reports_dir(cfg.root_dir, cfg.reports_dirname)
    write_csv_header(report_paths.report_csv_path)

    recup_dirs = list_recup_dirs(cfg.root_dir, cfg.process_recup_prefix)
    if not recup_dirs:
        raise FileNotFoundError(
            f"No se encontraron carpetas '{cfg.process_recup_prefix}*' dentro de: {cfg.root_dir}"
        )

    stats_total = PurgeStats()

    for recup_dir in recup_dirs:
        if os.path.basename(recup_dir) in cfg.exclude_dirnames:
            continue

        print(f"--- Procesando: {recup_dir} ---")
        stats_dir = PurgeStats()

        for entry in iter_files_in_dir(recup_dir):
            stats_total.scanned_files += 1
            stats_dir.scanned_files += 1

            should_delete, reason = _should_delete_by_type(cfg, entry.extension, entry.size_bytes)
            _apply_decision(
                entry=entry,
                should_delete=should_delete,
                reason=reason,
                dry_run=cfg.dry_run,
                report_csv=report_paths.report_csv_path,
                stats_total=stats_total,
                stats_dir=stats_dir,
            )

        _print_summary(stats_dir, stats_total, report_paths.report_csv_path)

    _print_total(stats_total, report_paths.report_csv_path)
    return report_paths.report_csv_path


# ── Purge small images ──────────────────────────────────────────────


def _should_delete_by_dimensions(
    cfg: PurgeSmallImagesConfig, width: int, height: int
) -> Tuple[bool, str]:
    if width < cfg.min_width or height < cfg.min_height:
        return True, f"below_min_dimensions_{width}x{height}"

    ratio = max(width, height) / max(min(width, height), 1)
    if ratio > cfg.max_aspect_ratio:
        return True, f"extreme_aspect_ratio_{ratio:.1f}"

    return False, "dimensions_ok"


def purge_small_images(cfg: PurgeSmallImagesConfig) -> str:
    from PIL import Image

    report_paths = ensure_reports_dir(cfg.root_dir, cfg.reports_dirname)
    write_csv_header(report_paths.report_csv_path)

    recup_dirs = list_recup_dirs(cfg.root_dir, cfg.process_recup_prefix)
    if not recup_dirs:
        raise FileNotFoundError(
            f"No se encontraron carpetas '{cfg.process_recup_prefix}*' dentro de: {cfg.root_dir}"
        )

    stats_total = PurgeStats()

    for recup_dir in recup_dirs:
        if os.path.basename(recup_dir) in cfg.exclude_dirnames:
            continue

        print(f"--- Procesando: {recup_dir} ---")
        stats_dir = PurgeStats()

        for entry in iter_files_in_dir(recup_dir):
            if entry.extension not in IMAGE_EXTENSIONS:
                continue

            stats_total.scanned_files += 1
            stats_dir.scanned_files += 1

            try:
                with Image.open(entry.path) as img:
                    width, height = img.size
            except Exception:
                _apply_decision(
                    entry=entry,
                    should_delete=False,
                    reason="unreadable_image",
                    dry_run=cfg.dry_run,
                    report_csv=report_paths.report_csv_path,
                    stats_total=stats_total,
                    stats_dir=stats_dir,
                )
                continue

            should_delete, reason = _should_delete_by_dimensions(cfg, width, height)
            _apply_decision(
                entry=entry,
                should_delete=should_delete,
                reason=reason,
                dry_run=cfg.dry_run,
                report_csv=report_paths.report_csv_path,
                stats_total=stats_total,
                stats_dir=stats_dir,
            )

        _print_summary(stats_dir, stats_total, report_paths.report_csv_path)

    _print_total(stats_total, report_paths.report_csv_path)
    return report_paths.report_csv_path


# ── Purge short videos ─────────────────────────────────────────────


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


def _get_video_duration(ffprobe_path: str, file_path: str) -> Optional[float]:
    """Obtiene la duración de un video en segundos usando ffprobe."""
    try:
        result = subprocess.run(
            [
                ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                file_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        duration_str = data.get("format", {}).get("duration")
        if duration_str is None:
            return None
        return float(duration_str)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError, OSError):
        return None


def _should_delete_short_video(
    cfg: PurgeShortVideosConfig, duration: Optional[float], size_bytes: int
) -> Tuple[bool, str]:
    if size_bytes < cfg.min_size_bytes:
        return True, f"below_min_size_{size_bytes}B"

    if duration is not None and duration < cfg.min_duration_secs:
        return True, f"below_min_duration_{duration:.1f}s"

    return False, "video_ok"


def purge_short_videos(cfg: PurgeShortVideosConfig) -> str:
    ffprobe_path = _find_ffprobe()
    print(f"Usando ffprobe: {ffprobe_path}")

    report_paths = ensure_reports_dir(cfg.root_dir, cfg.reports_dirname)
    write_csv_header(report_paths.report_csv_path)

    recup_dirs = list_recup_dirs(cfg.root_dir, cfg.process_recup_prefix)
    if not recup_dirs:
        raise FileNotFoundError(
            f"No se encontraron carpetas '{cfg.process_recup_prefix}*' dentro de: {cfg.root_dir}"
        )

    stats_total = PurgeStats()

    for recup_dir in recup_dirs:
        if os.path.basename(recup_dir) in cfg.exclude_dirnames:
            continue

        print(f"--- Procesando: {recup_dir} ---")
        stats_dir = PurgeStats()

        for entry in iter_files_in_dir(recup_dir):
            if entry.extension not in VIDEO_EXTENSIONS:
                continue

            stats_total.scanned_files += 1
            stats_dir.scanned_files += 1

            duration = _get_video_duration(ffprobe_path, entry.path)

            should_delete, reason = _should_delete_short_video(
                cfg, duration, entry.size_bytes
            )
            _apply_decision(
                entry=entry,
                should_delete=should_delete,
                reason=reason,
                dry_run=cfg.dry_run,
                report_csv=report_paths.report_csv_path,
                stats_total=stats_total,
                stats_dir=stats_dir,
            )

        _print_summary(stats_dir, stats_total, report_paths.report_csv_path)

    _print_total(stats_total, report_paths.report_csv_path)
    return report_paths.report_csv_path
