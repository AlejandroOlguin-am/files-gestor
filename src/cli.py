from __future__ import annotations

import argparse
import os
import sys

from files_gestor.purge import purge_by_type
from files_gestor.rules import DEFAULT_ALLOWED_EXTENSIONS, PurgeByTypeConfig


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

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
