import argparse
from .validate import cmd_validate
from .transition import cmd_transition

def main():
    p = argparse.ArgumentParser(prog="cinev2-cli")
    sp = p.add_subparsers(dest="cmd", required=True)

    p_val = sp.add_parser("validate", help="Validate DURUM.json against schema")
    p_val.add_argument("path")
    p_val.set_defaults(func=cmd_validate)

    p_tr = sp.add_parser("transition", help="Transition a shot status")
    p_tr.add_argument("path")
    p_tr.add_argument("shot_id")
    p_tr.add_argument("--to", required=True, choices=["PLANNED","IN_PROGRESS","BLOCKED","DONE"])
    p_tr.set_defaults(func=cmd_transition)

    args = p.parse_args()
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())

