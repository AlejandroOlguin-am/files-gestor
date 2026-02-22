from __future__ import annotations

import os
import shutil
from dataclasses import dataclass

from .report import append_organize_csv_row, ensure_reports_dir, write_organize_csv_header
from .rules import PHASH_EXTENSIONS, DetectFacesConfig
from .scan import iter_files_in_dir, list_recup_dirs


@dataclass
class FacesStats:
    scanned: int = 0
    moved: int = 0
    kept: int = 0
    errors: int = 0
    bytes_moved: int = 0


def _check_mediapipe() -> None:
    try:
        import mediapipe  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "mediapipe no está instalado.\n"
            "Instálalo con: pip install mediapipe\n"
            f"Error original: {exc}"
        ) from exc


def _count_faces(img, detector) -> int:
    """Cuenta caras en img (PIL.Image) usando detector mediapipe reutilizable.

    Retorna:
        >= 0  número de caras detectadas
        -1    error durante detección
    """
    try:
        import numpy as np
        rgb = np.array(img.convert("RGB"))
        results = detector.process(rgb)
        if results.detections is None:
            return 0
        return len(results.detections)
    except Exception:
        return -1


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


def detect_faces(cfg: DetectFacesConfig) -> str:
    """Mueve imágenes con caras detectadas a cfg.output_dir."""
    _check_mediapipe()

    import mediapipe as mp
    from PIL import Image

    report_paths = ensure_reports_dir(cfg.root_dir, cfg.reports_dirname, prefix="detect_faces")
    write_organize_csv_header(report_paths.report_csv_path)

    recup_dirs = list_recup_dirs(cfg.root_dir, cfg.process_recup_prefix)
    if not recup_dirs:
        raise FileNotFoundError(
            f"No se encontraron carpetas '{cfg.process_recup_prefix}*' dentro de: {cfg.root_dir}"
        )

    # Recolectar entradas de imagen primero para reportar progreso total
    all_entries = []
    for recup_dir in recup_dirs:
        if os.path.basename(recup_dir) in cfg.exclude_dirnames:
            continue
        for entry in iter_files_in_dir(recup_dir):
            if entry.extension in PHASH_EXTENSIONS or entry.extension in {".heic", ".heif"}:
                all_entries.append(entry)

    total = len(all_entries)
    stats = FacesStats()

    print(f"Total imágenes a procesar: {total}")

    with mp.solutions.face_detection.FaceDetection(
        min_detection_confidence=cfg.min_detection_confidence
    ) as detector:
        for entry in all_entries:
            stats.scanned += 1

            if stats.scanned % 100 == 0:
                print(f"{stats.scanned}/{total} procesadas...")

            # HEIC/HEIF — sin decoder PIL disponible
            if entry.extension in {".heic", ".heif"}:
                append_organize_csv_row(
                    report_paths.report_csv_path,
                    action="keep",
                    dry_run=cfg.dry_run,
                    reason="heic_skipped_no_decoder",
                    extension=entry.extension,
                    size_bytes=entry.size_bytes,
                    source_path=entry.path,
                    destination_path="",
                )
                stats.kept += 1
                continue

            try:
                img = Image.open(entry.path)
                img.load()
            except Exception:
                append_organize_csv_row(
                    report_paths.report_csv_path,
                    action="keep",
                    dry_run=cfg.dry_run,
                    reason="unreadable_image",
                    extension=entry.extension,
                    size_bytes=entry.size_bytes,
                    source_path=entry.path,
                    destination_path="",
                )
                stats.errors += 1
                continue

            n = _count_faces(img, detector)

            if n == -1:
                append_organize_csv_row(
                    report_paths.report_csv_path,
                    action="keep",
                    dry_run=cfg.dry_run,
                    reason="detection_error",
                    extension=entry.extension,
                    size_bytes=entry.size_bytes,
                    source_path=entry.path,
                    destination_path="",
                )
                stats.errors += 1
                continue

            if n == 0:
                append_organize_csv_row(
                    report_paths.report_csv_path,
                    action="keep",
                    dry_run=cfg.dry_run,
                    reason="no_faces",
                    extension=entry.extension,
                    size_bytes=entry.size_bytes,
                    source_path=entry.path,
                    destination_path="",
                )
                stats.kept += 1
                continue

            # n >= 1: mover a output_dir
            dest = os.path.join(cfg.output_dir, os.path.basename(entry.path))
            reason = f"faces_detected_{n}"

            if not cfg.dry_run:
                dest = _safe_dest(dest)
                os.makedirs(cfg.output_dir, exist_ok=True)
                try:
                    shutil.move(entry.path, dest)
                    stats.bytes_moved += entry.size_bytes
                except OSError as exc:
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
                    stats.errors += 1
                    continue
            else:
                stats.bytes_moved += entry.size_bytes

            append_organize_csv_row(
                report_paths.report_csv_path,
                action="move",
                dry_run=cfg.dry_run,
                reason=reason,
                extension=entry.extension,
                size_bytes=entry.size_bytes,
                source_path=entry.path,
                destination_path=dest,
            )
            stats.moved += 1

    print("-" * 40)
    dry_tag = " [DRY-RUN]" if cfg.dry_run else ""
    print(
        f"Resumen TOTAL{dry_tag}: scanned={stats.scanned} "
        f"movidas={stats.moved} "
        f"conservadas={stats.kept} "
        f"errores={stats.errors} "
        f"({stats.bytes_moved / 1_000_000:.1f} MB movidos)"
    )
    print(f"Reporte CSV: {report_paths.report_csv_path}")

    return report_paths.report_csv_path
