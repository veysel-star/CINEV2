
# --- CineV4 quick-route (do not disturb existing CLI) ---
import sys as _sys
if len(_sys.argv) >= 2 and _sys.argv[1] in ("manifest", "verify-manifest"):
    cmd = _sys.argv[1]
    rest = _sys.argv[2:]
    if cmd == "manifest":
        from .manifest import main as _m
        _m(rest)
        raise SystemExit(0)
    if cmd == "verify-manifest":
        from .verify_manifest import main as _v
        _v(rest)
        raise SystemExit(0)
# --- end CineV4 quick-route ---

import argparse

from .validate import cmd_validate
from .transition import cmd_transition
from .release import cmd_release
from .qc import cmd_qc
from .newshot import cmd_newshot
from .listshots import cmd_listshots
from tools.cli.render import cmd_render

def main():
    p = argparse.ArgumentParser(prog="cinev2-cli")
    sp = p.add_subparsers(dest="cmd", required=True)
    p_val = sp.add_parser("validate", help="Validate DURUM.json against schema")
    p_val.add_argument("path")
    p_val.set_defaults(func=cmd_validate)
    p_ns = sp.add_parser("newshot", help="Create a new shot skeleton")
    p_ns.add_argument("path")
    p_ns.add_argument("shot_id")
    p_ns.add_argument("--prompt", required=True)
    p_ns.set_defaults(func=cmd_newshot)
    p_tr = sp.add_parser("transition", help="Transition a shot status")
    p_tr.add_argument("path")
    p_tr.add_argument("shot_id")
    p_tr.add_argument(
        "--to", 
        required=True, 
        choices=["IN_PROGRESS", "QC", "DONE", "BLOCKED", "RETRY", "FAIL"],
    )
    p_tr.set_defaults(func=cmd_transition)
    p_rel = sp.add_parser("release", help="Build a release package from DONE shots")
    p_rel.add_argument("path")
    p_rel.add_argument("--out", required=True, help="Output directory (e.g. releases)")
    p_rel.add_argument("--release-id", default=None, help="Optional release folder name (default: UTC timestamp)")
    p_rel.set_defaults(func=cmd_release)
    p_qc = sp.add_parser("qc", help="generate qc.json for a shot")
    p_qc.add_argument("durum")
    p_qc.add_argument("shot_id") 
    p_qc.add_argument("--out", required=True)
    p_qc.set_defaults(func=cmd_qc)
    p_ls = sp.add_parser("listshots", help="List shots in DURUM.json")
    p_ls.add_argument("path", help="Path to DURUM.json")
    p_ls.add_argument("--status", default=None, help="Filter by status (e.g. DONE, QC, IN_PROGRESS, PLANNED)")
    p.add_argument("--phase", default=None, help="Filter by phase (e.g. FAZ_1)")
    p_ls.set_defaults(func=cmd_listshots)
    p_render = sp.add_parser("render", help="render preview artifact")
    p_render.add_argument("path", help="Path to DURUM.json")
    p_render.add_argument("shot_id", help="Shot id (e.g. SH008)")
    p_render.add_argument("--out", required=True, help="Output dir")
    p_render.add_argument("--src", required=True, help="Source preview.mp4")
    p_render.set_defaults(func=cmd_render)

    args = p.parse_args()
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())


