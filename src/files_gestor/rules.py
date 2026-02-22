from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet


DEFAULT_ALLOWED_EXTENSIONS: FrozenSet[str] = frozenset(
    {
        # Images (gifs are excluded)
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
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


IMAGE_EXTENSIONS: FrozenSet[str] = frozenset(
    {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
        ".heic",
        ".heif",
    }
)


@dataclass(frozen=True)
class PurgeSmallImagesConfig:
    root_dir: str
    process_recup_prefix: str = "recup_dir"

    dry_run: bool = True

    min_width: int = 200
    min_height: int = 200
    max_aspect_ratio: float = 5.0

    reports_dirname: str = "_reports"
    exclude_dirnames: FrozenSet[str] = frozenset({"_reports"})


VIDEO_EXTENSIONS: FrozenSet[str] = frozenset(
    {
        ".mp4",
        ".mov",
        ".mkv",
        ".avi",
        ".3gp",
        ".mts",
        ".m4v",
        ".wmv",
    }
)


@dataclass(frozen=True)
class PurgeShortVideosConfig:
    root_dir: str
    process_recup_prefix: str = "recup_dir"

    dry_run: bool = True

    min_duration_secs: float = 5.0
    min_size_bytes: int = 500_000  # 500 KB

    reports_dirname: str = "_reports"
    exclude_dirnames: FrozenSet[str] = frozenset({"_reports"})


@dataclass(frozen=True)
class DeduplicateConfig:
    root_dir: str
    process_recup_prefix: str = "recup_dir"

    dry_run: bool = True

    reports_dirname: str = "_reports"
    exclude_dirnames: FrozenSet[str] = frozenset({"_reports"})


DOC_EXTENSIONS: FrozenSet[str] = frozenset({".pdf", ".docx", ".pptx"})


# Extensiones con soporte PIL confiable para pHash.
# HEIC/HEIF excluido: Pillow requiere el paquete opcional pillow-heif.
# Para habilitarlas: pip install pillow-heif y agregar ".heic"/".heif" aquí.
PHASH_EXTENSIONS: FrozenSet[str] = frozenset({
    ".jpg", ".jpeg", ".png", ".webp", ".bmp",
})


@dataclass(frozen=True)
class PurgeSimilarImagesConfig:
    root_dir: str
    process_recup_prefix: str = "recup_dir"

    dry_run: bool = True

    # Distancia Hamming máxima entre pHashes para considerar imágenes similares.
    # 0 = solo duplicados exactos de pHash; 10 = agrupa versiones WhatsApp; 64 = todo igual.
    max_distance: int = 10

    # Límite O(n²): si hay más singletons que este valor, se omite la fase difusa.
    fuzzy_cap: int = 5_000

    reports_dirname: str = "_reports"
    exclude_dirnames: FrozenSet[str] = frozenset({"_reports"})


@dataclass(frozen=True)
class OrganizeConfig:
    root_dir: str
    output_dir: str
    process_recup_prefix: str = "recup_dir"

    dry_run: bool = True
    move: bool = False

    reports_dirname: str = "_reports"
    exclude_dirnames: FrozenSet[str] = frozenset({"_reports"})


@dataclass(frozen=True)
class ClassifyTextImagesConfig:
    root_dir: str
    output_dir: str                          # carpeta destino para imágenes con texto
    process_recup_prefix: str = "recup_dir"
    dry_run: bool = True
    text_threshold: float = 0.30             # fracción [0-1] de píxeles cubiertos por texto
    reports_dirname: str = "_reports"
    exclude_dirnames: FrozenSet[str] = frozenset({"_reports"})
