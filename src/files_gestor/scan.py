from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Iterator, Optional


@dataclass(frozen=True)
class FileEntry:
    path: str
    name: str
    size_bytes: int
    extension: str


def list_recup_dirs(root_dir: str, prefix: str = "recup_dir") -> list[str]:
    try:
        names = os.listdir(root_dir)
    except FileNotFoundError:
        return []

    dirs: list[str] = []
    for name in names:
        full = os.path.join(root_dir, name)
        if os.path.isdir(full) and name.startswith(prefix):
            dirs.append(full)
    dirs.sort()
    return dirs


def iter_files_in_dir(dir_path: str) -> Iterator[FileEntry]:
    for root, _dirs, files in os.walk(dir_path):
        for filename in files:
            full_path = os.path.join(root, filename)
            try:
                st = os.stat(full_path)
            except OSError:
                continue

            _base, ext = os.path.splitext(filename)
            yield FileEntry(
                path=full_path,
                name=filename,
                size_bytes=int(st.st_size),
                extension=ext.lower(),
            )
