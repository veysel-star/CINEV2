import argparse

from .validate import cmd_validate
from .transition import cmd_transition
from .release import cmd_release

def main():
    p = argparse.ArgumentParser(prog="cinev2-cli")
    sp = p.add_subparsers(dest="cmd", required=True)

    p_val = sp.add_parser("validate", help="Validate DURUM.json against schema")
    p_val.add_argument("path")
    p_val.set_defaults(func=cmd_validate)

    p_tr = sp.add_parser("transition", help="Transition a shot status")
    p_tr.add_argument("path")
    p_tr.add_argument("shot_id")
    p_tr.add_argument("--to", required=True, choices=["IN_PROGRESS", "QC", "DONE", "BLOCKED"])
    p_tr.set_defaults(func=cmd_transition)
    p_rel = sp.add_parser("release", help="Build a release package from DONE shots")
    p_rel.add_argument("path")
    p_rel.add_argument("--out", required=True, help="Output directory (e.g. releases)")
    p_rel.add_argument("--release-id", default=None, help="Optional release folder name (default: UTC timestamp)")
    p_rel.set_defaults(func=cmd_release)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())


