import json
import shutil
import hashlib
from datetime import datetime, timezone
from pathlib import Path


def _utc_id() -> str:
    # e.g. 20260101T221530Z
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .strftime("%Y%m%dT%H%M%SZ")
    )


def _fail(msg: str) -> int:
    print(f"[ERR] {msg}")
    return 2


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_release(args) -> int:
    durum_path = Path(args.path)
    out_root = Path(args.out)
    release_id = args.release_id or _utc_id()

    if not durum_path.exists() or not durum_path.is_file():
        return _fail(f"cannot read {durum_path}")

    try:
        durum = json.loads(durum_path.read_text(encoding="utf-8"))
    except Exception as e:
        return _fail(f"invalid json: {e}")

    shots = durum.get("shots")
    if not isinstance(shots, dict):
        return _fail("DURUM.json: 'shots' must be an object")

    done_ids = []
    for sid, shot in shots.items():
        if isinstance(shot, dict) and shot.get("status") == "DONE":
            done_ids.append(sid)

    if len(done_ids) == 0:
        return _fail("no DONE shots found; nothing to release")

    durum_dir = durum_path.resolve().parent
    release_dir = (out_root / release_id).resolve()

    # Build manifest entries
    manifest = {
        "release_id": release_id,
        "source_durum": str(durum_path),
        "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "shots": [],
    }

    # Ensure directory exists
    release_dir.mkdir(parents=True, exist_ok=True)

    for sid in sorted(done_ids):
        shot = shots[sid]
        outputs = shot.get("outputs") if isinstance(shot, dict) else None
        if not isinstance(outputs, dict) or len(outputs) == 0:
            return _fail(f"{sid}: DONE requires non-empty outputs")

        # --- HARD RELEASE GATE: required keys must exist in outputs ---
        required_keys = ["qc.json", "preview.mp4"]
        for k in required_keys:
            if k not in outputs:
                return _fail(f"{sid}: DONE requires outputs['{k}']")
        # ------------------------------------------------------------

        shot_block = {
            "shot_id": sid,
            "files": []
        }

        # Copy each output file into releases/<id>/<shot_id>/<key_basename>
        shot_out_dir = release_dir / sid
        shot_out_dir.mkdir(parents=True, exist_ok=True)

        for out_key in sorted(outputs.keys()):
            rel = outputs[out_key]

            if not isinstance(rel, str) or rel.strip() == "":
                return _fail(f"{sid}: outputs['{out_key}'] must be a non-empty string path")

            src = (durum_dir / rel).resolve()

            if not src.exists() or not src.is_file():
                return _fail(f"{sid}: outputs['{out_key}'] file missing on disk: {rel}")

            # Destination filename: keep key name but use original suffix if needed
            src_suffix = src.suffix
            dest_name = out_key
            if "." not in dest_name and src_suffix:
                dest_name = f"{out_key}{src_suffix}"

            dest = shot_out_dir / dest_name
            shutil.copy2(src, dest)

            size = dest.stat().st_size
            sha = _sha256_file(dest)

            rel_dest = str(Path(sid) / dest_name).replace("\\", "/")

            shot_block["files"].append({
                "key": out_key,
                "source": rel,
                "path": rel_dest,
                "dest": rel_dest,
                "bytes": size,
                "sha256": sha,
            })

        manifest["shots"].append(shot_block)

    # Write manifest.json and release.json (same content, different filename for convenience)
    (release_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (release_dir / "release.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"[OK] release created: {release_dir}")
    print(f"[OK] DONE shots: {len(done_ids)}")
    print(f"[OK] manifest: {release_dir / 'manifest.json'}")
    return 0

