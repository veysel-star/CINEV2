
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
from .promote_release import cmd_promote_release
from tools.cli.bundle import cmd_bundle


# --- CineV4 quick-route (do not disturb existing CLI) ---
import sys as _sys
if len(_sys.argv) >= 2 and _sys.argv[1] in ("manifest", "verify-manifest", "release-gate"):
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
    if cmd == "release-gate":
        from .release_gate import main as _rg
        _rg(rest)
        raise SystemExit(0)
# --- end CineV4 quick-route ---


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
        choices=["IN_PROGRESS", "QC", "DONE", "RELEASE", "BLOCKED", "RETRY", "FAIL"],
    )
    p_tr.add_argument("--release", default=None, help="Release id (e.g. demo01_r0001)")
    p_tr.set_defaults(func=cmd_transition)
    p_rel = sp.add_parser("release", help="Build a release package from DONE shots")
    p_rel.add_argument("path")
    p_rel.add_argument("--project", default=None, help="Project id (default: DURUM.active_project)")
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
    p_render.add_argument(
        "--force",
        action="store_true",
        help="Allow overwrite (disable strict render guard)"
    )
    p_render.add_argument("path", help="Path to DURUM.json")
    p_render.add_argument("shot_id", help="Shot id (e.g. SH008)")
    p_render.add_argument("--out", required=True, help="Output dir")
    p_render.add_argument(
        "--src",
        required=False,
        default=None,
        help="Source preview.mp4 (default: shot.outputs['preview.mp4'])"
    )
    p_render.set_defaults(func=cmd_render)
    p_pr = sp.add_parser("promote-release", help="Promote DONE shots to RELEASE (after release-gate)")
    p_pr.add_argument("path")
    p_pr.add_argument("--project", required=True, help="Project id (e.g. demo01)")
    p_pr.add_argument("--release", required=True, help="Release id (e.g. demo01_r0005)")
    g = p_pr.add_mutually_exclusive_group(required=True)
    g.add_argument("--all-done", action="store_true")
    g.add_argument(
        "--shots",
        nargs="+",
        help="Shot ids: SH001 SH002 ... (comma also ok: SH001,SH002)"
    )
    p_pr.set_defaults(func=cmd_promote_release)
    p_bundle = sp.add_parser("bundle", help="Create bundle release from multiple releases")

    p_bundle.add_argument(
        "--sources",
        nargs="+",
        required=True,
        help="Source release directories"
    )

    p_bundle.add_argument(
        "--bundle-id",
        help="Optional bundle id"
    )

    p_bundle.add_argument(
        "--shots",
        default=None,
        help="Comma-separated shot ids (e.g. SH041,SH042)"
    )

    p_bundle.add_argument(
        "--prefer",
        choices=["fail", "latest"],
        default="fail",
        help="Conflict resolution policy (default: fail)"
    )

    p_bundle.set_defaults(func=cmd_bundle)

    args = p.parse_args()
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())


