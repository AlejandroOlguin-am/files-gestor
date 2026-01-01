from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet


DEFAULT_ALLOWED_EXTENSIONS: FrozenSet[str] = frozenset(
    {
        # Images
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
        #".gif",
        ".heic",
        ".heif",

        # Videos
        ".mp4",
        ".mov",
        ".mkv",
        ".avi",
        ".3gp",
        ".mts",
        ".m4v",
        ".wmv",
        
        # Docs
        ".pdf",
        ".docx",
        ".pptx",
    }
)


@dataclass(frozen=True)
class PurgeByTypeConfig:
    root_dir: str
    allowed_extensions: FrozenSet[str] = DEFAULT_ALLOWED_EXTENSIONS
    process_recup_prefix: str = "recup_dir"

    dry_run: bool = True

    # Files with no extension are deleted if below this size
    no_extension_delete_below_bytes: int = 1_000_000

    # Report folder name within root_dir
    reports_dirname: str = "_reports"

    # Safety: never touch these folders
    exclude_dirnames: FrozenSet[str] = frozenset({"_reports"})
