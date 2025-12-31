# tools/cli/__main__.py
from __future__ import annotations

import argparse
import sys

from .validate import validate_durum


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cinev2-cli")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="Validate DURUM.json against schema")
    v.add_argument("durum_path", help="Path to DURUM.json")
    v.add_argument("--schema", default="schema/shot.schema.json", help="Path to shot schema json")

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.cmd == "validate":
        return validate_durum(args.durum_path, args.schema)

    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
