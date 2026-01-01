from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional


@dataclass(frozen=True)
class ReportPaths:
    reports_dir: str
    report_csv_path: str


def ensure_reports_dir(root_dir: str, reports_dirname: str = "_reports") -> ReportPaths:
    reports_dir = os.path.join(root_dir, reports_dirname)
    os.makedirs(reports_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_csv_path = os.path.join(reports_dir, f"purge_by_type_{ts}.csv")
    return ReportPaths(reports_dir=reports_dir, report_csv_path=report_csv_path)


def write_csv_header(path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "action",
                "dry_run",
                "reason",
                "extension",
                "size_bytes",
                "path",
            ]
        )


def append_csv_row(
    path: str,
    *,
    action: str,
    dry_run: bool,
    reason: str,
    extension: str,
    size_bytes: int,
    file_path: str,
) -> None:
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([action, str(dry_run), reason, extension, str(size_bytes), file_path])
