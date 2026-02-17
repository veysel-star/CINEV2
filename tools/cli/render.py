import argparse
import json
import os
import shutil
import sys
import hashlib
from pathlib import Path

# strict by default: do not overwrite existing preview.mp4 unless --force
STRICT_RENDER = True


def _fail(msg: str) -> int:
    print("[ERR]", msg)
    return 2


def _ok(msg: str) -> int:
    print("[OK]", msg)
    return 0


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_render(args) -> int:
    # bind --force to strictness (force disables strict overwrite guard)
    global STRICT_RENDER
    if getattr(args, "force", False):
        STRICT_RENDER = False

    repo_root = Path(__file__).resolve().parents[2]  # tools/cli/render.py -> repo root

    # args
    durum_path = Path(args.path)
    shot_id = (args.shot_id or "").strip()
    out_arg = args.out
    src_arg = getattr(args, "src", None)

    if not durum_path.exists():
        return _fail(f"DURUM not found: {durum_path}")
    if not shot_id:
        return _fail("missing shot_id")
    if not out_arg:
        return _fail("missing --out")

    try:
        durum = json.loads(durum_path.read_text(encoding="utf-8"))
    except Exception as e:
        return _fail(f"DURUM invalid JSON: {e}")

    shots = (durum or {}).get("shots") or {}
    if shot_id not in shots:
        return _fail(f"unknown shot: {shot_id}")

    shot = shots[shot_id]
    outputs = shot.get("outputs") or {}
    if not isinstance(outputs, dict):
        outputs = {}

    # resolve OUT (must be inside repo and under outputs/)
    out_dir = (repo_root / out_arg).resolve()
    try:
        out_dir.relative_to(repo_root)
    except Exception:
        return _fail("out must be inside repo root")

    out_rel = out_dir.relative_to(repo_root).as_posix()
    if not out_rel.startswith("outputs/"):
        return _fail("out must be under outputs/")

    os.makedirs(out_dir, exist_ok=True)
    dst = out_dir / "preview.mp4"

    # resolve SRC:
    # - if --src provided: use it
    # - else: use shot.outputs["preview.mp4"]
    if src_arg is None or str(src_arg).strip() == "":
        src_rel_from_state = outputs.get("preview.mp4")
        if not src_rel_from_state:
            return _fail("missing --src and shot.outputs['preview.mp4'] is not set")
        src_path = (repo_root / str(src_rel_from_state)).resolve()
    else:
        src_path = (repo_root / str(src_arg)).resolve()

    try:
        src_path.relative_to(repo_root)
    except Exception:
        return _fail("src must be inside repo root")

    if not src_path.exists():
        return _fail(f"src not found: {src_path}")

    # prevent copying file onto itself
    try:
        if dst.exists() and dst.samefile(src_path):
            return _fail("refusing to overwrite the same file (src == dst)")
    except Exception:
        pass

    # idempotency + overwrite policy
    if dst.exists():
        try:
            src_h = _sha256(src_path)
            dst_h = _sha256(dst)
        except Exception as e:
            return _fail(f"hash failed: {e}")

        # if identical -> OK (idempotent), do not rewrite even in strict mode
        if src_h == dst_h:
            # still ensure DURUM points to this out
            outputs["preview.mp4"] = f"{out_rel}/preview.mp4"
            shot["outputs"] = outputs
            try:
                durum_path.write_text(json.dumps(durum, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception as e:
                return _fail(f"failed to write DURUM: {e}")
            return _ok(f"{shot_id}: preview.mp4 already up-to-date ({out_rel}/preview.mp4)")

        # different content
        if STRICT_RENDER:
            return _fail("preview.mp4 already exists (strict mode, no overwrite). Use --force to overwrite.")

    # copy (overwrite if dst exists and not strict or --force)
    try:
        shutil.copy2(src_path, dst)
    except Exception as e:
        return _fail(f"copy failed: {e}")

    # update DURUM outputs to point to new artifact
    outputs["preview.mp4"] = f"{out_rel}/preview.mp4"
    shot["outputs"] = outputs

    try:
        durum_path.write_text(json.dumps(durum, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        return _fail(f"failed to write DURUM: {e}")

    return _ok(f"{shot_id}: wrote {out_rel}/preview.mp4")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="cinev2-cli render")
    p.add_argument("--force", action="store_true", help="Allow overwrite (disable strict render guard)")
    p.add_argument("path", help="Path to DURUM.json")
    p.add_argument("shot_id", help="Shot id (e.g. SH001)")
    p.add_argument("--out", required=True, help="Output dir (must be under outputs/)")
    p.add_argument("--src", required=False, default=None, help="Source preview.mp4 (default: shot.outputs['preview.mp4'])")
    args = p.parse_args(argv)
    return cmd_render(args)


if __name__ == "__main__":
    raise SystemExit(main())

