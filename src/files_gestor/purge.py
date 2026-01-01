from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Tuple

from .report import append_csv_row, ensure_reports_dir, write_csv_header
from .rules import PurgeByTypeConfig
from .scan import iter_files_in_dir, list_recup_dirs


@dataclass
class PurgeStats:
    scanned_files: int = 0
    deleted_files: int = 0
    kept_files: int = 0
    errors: int = 0

    deleted_bytes: int = 0
    kept_bytes: int = 0


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
        # Safety: ignore reports folder if it happens to match walk
        if os.path.basename(recup_dir) in cfg.exclude_dirnames:
            continue

        print(f"--- Procesando: {recup_dir} ---")
        stats_dir = PurgeStats()

        for entry in iter_files_in_dir(recup_dir):
            stats_total.scanned_files += 1
            stats_dir.scanned_files += 1

            should_delete, reason = _should_delete_by_type(cfg, entry.extension, entry.size_bytes)

            if should_delete:
                append_csv_row(
                    report_paths.report_csv_path,
                    action="delete",
                    dry_run=cfg.dry_run,
                    reason=reason,
                    extension=entry.extension,
                    size_bytes=entry.size_bytes,
                    file_path=entry.path,
                )

                if cfg.dry_run:
                    stats_total.deleted_files += 1
                    stats_dir.deleted_files += 1
                    stats_total.deleted_bytes += entry.size_bytes
                    stats_dir.deleted_bytes += entry.size_bytes
                    continue

                try:
                    os.remove(entry.path)
                    stats_total.deleted_files += 1
                    stats_dir.deleted_files += 1
                    stats_total.deleted_bytes += entry.size_bytes
                    stats_dir.deleted_bytes += entry.size_bytes
                except OSError:
                    stats_total.errors += 1
                    stats_dir.errors += 1
                continue

            # kept
            append_csv_row(
                report_paths.report_csv_path,
                action="keep",
                dry_run=cfg.dry_run,
                reason=reason,
                extension=entry.extension,
                size_bytes=entry.size_bytes,
                file_path=entry.path,
            )
            stats_total.kept_files += 1
            stats_dir.kept_files += 1
            stats_total.kept_bytes += entry.size_bytes
            stats_dir.kept_bytes += entry.size_bytes

        print(
            "Resumen carpeta: "
            f"scanned={stats_dir.scanned_files} "
            f"delete={stats_dir.deleted_files} "
            f"keep={stats_dir.kept_files} "
            f"errors={stats_dir.errors}"
        )

    print("-" * 40)
    print(
        "Resumen TOTAL: "
        f"scanned={stats_total.scanned_files} "
        f"delete={stats_total.deleted_files} "
        f"keep={stats_total.kept_files} "
        f"errors={stats_total.errors}"
    )
    print(f"Reporte CSV: {report_paths.report_csv_path}")

    return report_paths.report_csv_path
