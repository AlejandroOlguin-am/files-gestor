from __future__ import annotations

import argparse
import os
import sys

from files_gestor.organize import organize
from files_gestor.purge import deduplicate, purge_by_type, purge_similar_images, purge_small_images, purge_short_videos
from files_gestor.rules import (
    DEFAULT_ALLOWED_EXTENSIONS,
    DeduplicateConfig,
    OrganizeConfig,
    PurgeByTypeConfig,
    PurgeSimilarImagesConfig,
    PurgeShortVideosConfig,
    PurgeSmallImagesConfig,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="files-gestor")

    sub = parser.add_subparsers(dest="command", required=True)

    p_purge = sub.add_parser(
        "purge-by-type",
        help="Elimina archivos que NO están en la whitelist (solo dentro de recup_dir.*).",
    )
    p_purge.add_argument("--root", required=True, help="Ruta a testdisk-7.3-WIP")
    p_purge.add_argument(
        "--apply",
        action="store_true",
        help="Ejecuta borrado real (si no se indica, es dry-run).",
    )
    p_purge.add_argument(
        "--recup-prefix",
        default="recup_dir",
        help="Prefijo de carpetas a procesar (default: recup_dir)",
    )
    p_purge.add_argument(
        "--noext-delete-below-mb",
        type=float,
        default=1.0,
        help="Borra archivos sin extensión si son menores a este tamaño (MB). Default: 1.0",
    )

    # ── purge-small-images ──
    p_small = sub.add_parser(
        "purge-small-images",
        help="Elimina imágenes pequeñas (iconos, thumbnails) y con aspect ratio extremo.",
    )
    p_small.add_argument("--root", required=True, help="Ruta a testdisk-7.3-WIP")
    p_small.add_argument(
        "--apply",
        action="store_true",
        help="Ejecuta borrado real (si no se indica, es dry-run).",
    )
    p_small.add_argument(
        "--recup-prefix",
        default="recup_dir",
        help="Prefijo de carpetas a procesar (default: recup_dir)",
    )
    p_small.add_argument(
        "--min-width",
        type=int,
        default=200,
        help="Ancho mínimo en px (default: 200)",
    )
    p_small.add_argument(
        "--min-height",
        type=int,
        default=200,
        help="Alto mínimo en px (default: 200)",
    )
    p_small.add_argument(
        "--max-aspect-ratio",
        type=float,
        default=5.0,
        help="Aspect ratio máximo permitido (default: 5.0)",
    )

    # ── purge-short-videos ──
    p_video = sub.add_parser(
        "purge-short-videos",
        help="Elimina videos cortos o muy pequeños (estados de WhatsApp, clips basura).",
    )
    p_video.add_argument("--root", required=True, help="Ruta a testdisk-7.3-WIP")
    p_video.add_argument(
        "--apply",
        action="store_true",
        help="Ejecuta borrado real (si no se indica, es dry-run).",
    )
    p_video.add_argument(
        "--recup-prefix",
        default="recup_dir",
        help="Prefijo de carpetas a procesar (default: recup_dir)",
    )
    p_video.add_argument(
        "--min-duration",
        type=float,
        default=5.0,
        help="Duración mínima en segundos (default: 5.0)",
    )
    p_video.add_argument(
        "--min-size-kb",
        type=float,
        default=500.0,
        help="Tamaño mínimo en KB (default: 500)",
    )

    # ── deduplicate ──
    p_dedup = sub.add_parser(
        "deduplicate",
        help="Elimina archivos duplicados (mismo hash SHA-256).",
    )
    p_dedup.add_argument("--root", required=True, help="Ruta a testdisk-7.3-WIP")
    p_dedup.add_argument(
        "--apply",
        action="store_true",
        help="Ejecuta borrado real (si no se indica, es dry-run).",
    )
    p_dedup.add_argument(
        "--recup-prefix",
        default="recup_dir",
        help="Prefijo de carpetas a procesar (default: recup_dir)",
    )

    # ── purge-similar-images ──
    p_similar = sub.add_parser(
        "purge-similar-images",
        help="Elimina imágenes visualmente similares (pHash), conserva la de mayor tamaño.",
    )
    p_similar.add_argument("--root", required=True, help="Ruta a testdisk-7.3-WIP")
    p_similar.add_argument(
        "--apply",
        action="store_true",
        help="Ejecuta borrado real (si no se indica, es dry-run).",
    )
    p_similar.add_argument(
        "--recup-prefix",
        default="recup_dir",
        help="Prefijo de carpetas a procesar (default: recup_dir)",
    )
    p_similar.add_argument(
        "--max-distance",
        type=int,
        default=10,
        help="Distancia Hamming máxima entre pHashes (0=exacto, 10=WhatsApp, default: 10)",
    )
    p_similar.add_argument(
        "--fuzzy-cap",
        type=int,
        default=5_000,
        help="Límite de singletons para la fase difusa O(n²) (default: 5000)",
    )

    # ── organize ──
    p_org = sub.add_parser(
        "organize",
        help="Copia (o mueve) archivos de recup_dir.* a una carpeta organizada por tipo y fecha.",
    )
    p_org.add_argument("--root", required=True, help="Ruta a testdisk-7.3-WIP")
    p_org.add_argument("--output-dir", required=True, help="Carpeta destino (puede ser otro disco)")
    p_org.add_argument(
        "--apply",
        action="store_true",
        help="Ejecuta la operación real (si no se indica, es dry-run).",
    )
    p_org.add_argument(
        "--move",
        action="store_true",
        help="Mueve los archivos en vez de copiarlos.",
    )
    p_org.add_argument(
        "--recup-prefix",
        default="recup_dir",
        help="Prefijo de carpetas a procesar (default: recup_dir)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "purge-by-type":
        root = os.path.abspath(args.root)
        dry_run = not bool(args.apply)

        cfg = PurgeByTypeConfig(
            root_dir=root,
            dry_run=dry_run,
            process_recup_prefix=args.recup_prefix,
            no_extension_delete_below_bytes=int(args.noext_delete_below_mb * 1_000_000),
            allowed_extensions=DEFAULT_ALLOWED_EXTENSIONS,
        )

        if not cfg.dry_run:
            print("ATENCIÓN: BORRADO REAL ACTIVO.")
            print(f"Root: {cfg.root_dir}")
            print(f"Solo se procesarán carpetas: {cfg.process_recup_prefix}*")
            confirm = input("Escribe 'BORRAR' para confirmar: ").strip()
            if confirm != "BORRAR":
                print("Cancelado.")
                return 2

        purge_by_type(cfg)
        return 0

    if args.command == "purge-small-images":
        root = os.path.abspath(args.root)
        dry_run = not bool(args.apply)

        cfg = PurgeSmallImagesConfig(
            root_dir=root,
            dry_run=dry_run,
            process_recup_prefix=args.recup_prefix,
            min_width=args.min_width,
            min_height=args.min_height,
            max_aspect_ratio=args.max_aspect_ratio,
        )

        if not cfg.dry_run:
            print("ATENCIÓN: BORRADO REAL ACTIVO.")
            print(f"Root: {cfg.root_dir}")
            print(f"Filtro: imágenes < {cfg.min_width}x{cfg.min_height} px o aspect ratio > {cfg.max_aspect_ratio}")
            confirm = input("Escribe 'BORRAR' para confirmar: ").strip()
            if confirm != "BORRAR":
                print("Cancelado.")
                return 2

        purge_small_images(cfg)
        return 0

    if args.command == "purge-short-videos":
        root = os.path.abspath(args.root)
        dry_run = not bool(args.apply)

        cfg = PurgeShortVideosConfig(
            root_dir=root,
            dry_run=dry_run,
            process_recup_prefix=args.recup_prefix,
            min_duration_secs=args.min_duration,
            min_size_bytes=int(args.min_size_kb * 1_000),
        )

        if not cfg.dry_run:
            print("ATENCIÓN: BORRADO REAL ACTIVO.")
            print(f"Root: {cfg.root_dir}")
            print(f"Filtro: videos < {cfg.min_duration_secs}s o < {args.min_size_kb} KB")
            confirm = input("Escribe 'BORRAR' para confirmar: ").strip()
            if confirm != "BORRAR":
                print("Cancelado.")
                return 2

        purge_short_videos(cfg)
        return 0

    if args.command == "deduplicate":
        root = os.path.abspath(args.root)
        dry_run = not bool(args.apply)

        cfg = DeduplicateConfig(
            root_dir=root,
            dry_run=dry_run,
            process_recup_prefix=args.recup_prefix,
        )

        if not cfg.dry_run:
            print("ATENCIÓN: BORRADO REAL ACTIVO.")
            print(f"Root: {cfg.root_dir}")
            print("Se eliminarán archivos duplicados (mismo SHA-256).")
            confirm = input("Escribe 'BORRAR' para confirmar: ").strip()
            if confirm != "BORRAR":
                print("Cancelado.")
                return 2

        deduplicate(cfg)
        return 0

    if args.command == "purge-similar-images":
        root = os.path.abspath(args.root)
        dry_run = not bool(args.apply)

        cfg = PurgeSimilarImagesConfig(
            root_dir=root,
            dry_run=dry_run,
            process_recup_prefix=args.recup_prefix,
            max_distance=args.max_distance,
            fuzzy_cap=args.fuzzy_cap,
        )

        if not cfg.dry_run:
            print("ATENCIÓN: BORRADO REAL ACTIVO.")
            print(f"Root: {cfg.root_dir}")
            print(f"Distancia máxima pHash: {cfg.max_distance} bits Hamming")
            confirm = input("Escribe 'BORRAR' para confirmar: ").strip()
            if confirm != "BORRAR":
                print("Cancelado.")
                return 2

        purge_similar_images(cfg)
        return 0

    if args.command == "organize":
        root = os.path.abspath(args.root)
        output_dir = os.path.abspath(args.output_dir)
        dry_run = not bool(args.apply)

        cfg = OrganizeConfig(
            root_dir=root,
            output_dir=output_dir,
            dry_run=dry_run,
            move=args.move,
            process_recup_prefix=args.recup_prefix,
        )

        if not cfg.dry_run:
            action_word = "MOVER" if cfg.move else "COPIAR"
            print(f"ATENCIÓN: {'MOVER' if cfg.move else 'COPIAR'} REAL ACTIVO.")
            print(f"Root:   {cfg.root_dir}")
            print(f"Destino: {cfg.output_dir}")
            confirm = input(f"Escribe '{action_word}' para confirmar: ").strip()
            if confirm != action_word:
                print("Cancelado.")
                return 2

        organize(cfg)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
