# tools/cli/render.py
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False

def _resolve_under(root: Path, p: str) -> Path:
    pp = Path(p)
    if pp.is_absolute():
        return pp.resolve()
    return (root / pp).resolve()



def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fail(msg: str) -> int:
    print(f"[ERR] {msg}")
    return 2


def cmd_render(args) -> int:
    durum_path = Path(args.path).absolute()
    shot_id = args.shot_id

    # state root = DURUM.json'un bulunduğu klasör
    state_root = durum_path.parent.absolute()

    def _resolve_under(base: Path, p: str) -> Path:
        pp = Path(p)
        return pp.absolute() if pp.is_absolute() else (base / pp).absolute()

    def _is_within(child: Path, base: Path) -> bool:
        try:
            child.absolute().relative_to(base.absolute())
            return True
        except ValueError:
            return False

    out_dir = _resolve_under(state_root, args.out)
    src_path = _resolve_under(state_root, args.src)

    if not durum_path.exists() or not durum_path.is_file():
        return _fail(f"cannot read {durum_path}")

    if not src_path.exists() or not src_path.is_file():
        return _fail(f"src not found: {src_path}")

    # read DURUM
    try:
        durum = json.loads(durum_path.read_text(encoding="utf-8"))
    except Exception as e:
        return _fail(f"invalid json: {e}")

    shots = durum.get("shots")
    if not isinstance(shots, dict):
        return _fail("DURUM.json: 'shots' must be an object")

    shot = shots.get(shot_id)
    if not isinstance(shot, dict):
        return _fail(f"shot not found: {shot_id}")
    
    dst_path = out_dir / "preview.mp4"

    if not _is_within(dst_path, state_root):
        return _fail(f"--out must be under {state_root} (relative path contract)")

    if not _is_within(src_path, state_root):
        return _fail(f"--src must be under {state_root} (relative path contract)")


    # ensure out dir
    out_dir.mkdir(parents=True, exist_ok=True)

    
    # yazılacak path'i state_root'a göre relative kaydet
    rel_preview = dst_path.relative_to(state_root).as_posix()
 
    try:
        shutil.copyfile(src_path, dst_path)
    except Exception as e:
        return _fail(f"copy failed: {e}")

    outputs = shot.get("outputs") or {}
    if not isinstance(outputs, dict):
        outputs = {}
    outputs["preview.mp4"] = rel_preview
    shot["outputs"] = outputs

    # history event
    hist = shot.get("history") or []
    if not isinstance(hist, list):
        hist = []
    hist.append(
        {
            "event": "RENDERED",
            "at": _utc_now(),
            "by": "cli",
            "note": f"preview.mp4 <= {src_path.as_posix()} -> {rel_preview}",
        }
    )
    shot["history"] = hist

    # update top-level timestamp
    durum["last_updated_utc"] = _utc_now()

    # write back
    try:
        durum_path.write_text(json.dumps(durum, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception as e:
        return _fail(f"write failed: {e}")

    print(f"[OK] {shot_id}: wrote {rel_preview}")
    return 0
