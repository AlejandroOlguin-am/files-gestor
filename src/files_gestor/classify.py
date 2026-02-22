from __future__ import annotations

import os
import shutil
from dataclasses import dataclass

from .report import append_organize_csv_row, ensure_reports_dir, write_organize_csv_header
from .rules import PHASH_EXTENSIONS, ClassifyTextImagesConfig
from .scan import iter_files_in_dir, list_recup_dirs


@dataclass
class ClassifyStats:
    scanned: int = 0
    moved: int = 0
    kept: int = 0
    errors: int = 0
    bytes_moved: int = 0


def _check_tesseract() -> None:
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
    except Exception as exc:
        raise RuntimeError(
            "Tesseract no está instalado o no se encuentra en el PATH.\n"
            "Instálalo con: sudo apt install tesseract-ocr\n"
            f"Error original: {exc}"
        ) from exc


def _text_coverage(img) -> float:
    try:
        import pytesseract
        from PIL import Image

        width, height = img.size
        if width == 0 or height == 0:
            return 0.0

        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

        mask = Image.new("L", (width, height), 0)

        from PIL import ImageDraw
        draw = ImageDraw.Draw(mask)

        n_boxes = len(data["conf"])
        for i in range(n_boxes):
            try:
                conf = int(data["conf"][i])
            except (ValueError, TypeError):
                continue
            if conf > 0:
                left = data["left"][i]
                top = data["top"][i]
                w = data["width"][i]
                h = data["height"][i]
                draw.rectangle([left, top, left + w, top + h], fill=255)

        covered = sum(1 for px in mask.getdata() if px > 0)
        return covered / (width * height)
    except Exception:
        return 0.0


def _safe_dest(dest_path: str) -> str:
    if not os.path.exists(dest_path):
        return dest_path

    base, ext = os.path.splitext(dest_path)
    counter = 1
    while True:
        candidate = f"{base}_{counter}{ext}"
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def classify_text_images(cfg: ClassifyTextImagesConfig) -> str:
    _check_tesseract()

    from PIL import Image

    report_paths = ensure_reports_dir(cfg.root_dir, cfg.reports_dirname, prefix="classify_text_images")
    write_organize_csv_header(report_paths.report_csv_path)

    recup_dirs = list_recup_dirs(cfg.root_dir, cfg.process_recup_prefix)
    if not recup_dirs:
        raise FileNotFoundError(
            f"No se encontraron carpetas '{cfg.process_recup_prefix}*' dentro de: {cfg.root_dir}"
        )

    # Collect all image entries first for progress reporting
    all_entries = []
    for recup_dir in recup_dirs:
        if os.path.basename(recup_dir) in cfg.exclude_dirnames:
            continue
        for entry in iter_files_in_dir(recup_dir):
            if entry.extension in PHASH_EXTENSIONS or entry.extension in {".heic", ".heif"}:
                all_entries.append(entry)

    total = len(all_entries)
    stats = ClassifyStats()

    print(f"Total imágenes a procesar: {total}")

    for entry in all_entries:
        stats.scanned += 1

        if stats.scanned % 100 == 0:
            print(f"{stats.scanned}/{total} procesadas...")

        # Skip HEIC/HEIF — no decoder available
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

        coverage = _text_coverage(img)
        coverage_pct = int(coverage * 100)

        if coverage >= cfg.text_threshold:
            dest = os.path.join(cfg.output_dir, os.path.basename(entry.path))
            reason = f"text_coverage_{coverage_pct}pct"

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
        else:
            reason = f"text_coverage_ok_{coverage_pct}pct"
            append_organize_csv_row(
                report_paths.report_csv_path,
                action="keep",
                dry_run=cfg.dry_run,
                reason=reason,
                extension=entry.extension,
                size_bytes=entry.size_bytes,
                source_path=entry.path,
                destination_path="",
            )
            stats.kept += 1

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
