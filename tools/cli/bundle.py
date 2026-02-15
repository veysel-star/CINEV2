import os
import sys
import json
import shutil
import hashlib
from datetime import datetime, timezone


def _sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_created_utc(s: str) -> datetime:
    # expected: 2026-02-10T19:40:46Z
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _parse_shots_arg(shots_arg: str | None) -> set[str] | None:
    if not shots_arg:
        return None
    parts = []
    for x in shots_arg.split(","):
        x = x.strip()
        if x:
            parts.append(x)
    return set(parts) if parts else None


def _verify_manifest_or_exit(manifest_path: str):
    # IMPORTANT: we call verify_manifest's main directly (no subprocess)
    from .verify_manifest import main as verify_main
    try:
        verify_main([manifest_path])
    except SystemExit as e:
        code = int(getattr(e, "code", 1) or 1)
        if code != 0:
            raise
    except Exception:
        raise


def cmd_bundle(args):
    sources = args.sources
    bundle_id = args.bundle_id or datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    prefer = getattr(args, "prefer", "fail")  # fail|latest
    shots_filter = _parse_shots_arg(getattr(args, "shots", None))

    if not sources or len(sources) < 1:
        print("ERROR: --sources requires at least 1 source release directory")
        sys.exit(1)

    out_root = os.path.join("releases", bundle_id)
    if os.path.exists(out_root):
        print(f"ERROR: bundle release already exists: {out_root}")
        sys.exit(1)

    # 1) verify each source manifest first (production-grade requirement)
    loaded_sources = []
    for src in sources:
        manifest_path = os.path.join(src, "manifest.json")
        if not os.path.exists(manifest_path):
            print(f"ERROR: manifest not found: {manifest_path}")
            sys.exit(1)

        try:
            _verify_manifest_or_exit(manifest_path)
        except SystemExit:
            print(f"ERROR: source verify-manifest FAILED: {manifest_path}")
            sys.exit(1)

        with open(manifest_path, "r", encoding="utf-8") as f:
            m = json.load(f)

        # hard requirements
        if m.get("manifest_version") != 3:
            print(f"ERROR: unsupported manifest_version in {manifest_path}: {m.get('manifest_version')}")
            sys.exit(1)

        hash_alg = m.get("hash_alg") or "sha256"
        if m.get("hash_alg") is None:
            print(f"[WARN] hash_alg missing in {manifest_path}; assuming sha256 for backward compatibility")

        if hash_alg != "sha256":
            print(f"ERROR: unsupported hash_alg in {manifest_path}: {m.get('hash_alg')}")
            sys.exit(1)

        created_utc = m.get("created_utc")
        if not created_utc:
            print(f"ERROR: created_utc missing in {manifest_path}")
            sys.exit(1)

        loaded_sources.append({
            "src": src,
            "manifest_path": manifest_path,
            "manifest": m,
            "release_id": m.get("release_id"),
            "created_dt": _parse_created_utc(created_utc),
            "manifest_sha256": _sha256_of_file(manifest_path),
        })

    # 2) decide which shots to include + conflict handling
    chosen = {}  # shot_id -> (source_info, shot_obj)
    for s in loaded_sources:
        m = s["manifest"]
        for shot in m.get("shots", []):
            shot_id = shot.get("shot_id")
            if not shot_id:
                continue

            if shots_filter is not None and shot_id not in shots_filter:
                continue

            if shot_id not in chosen:
                chosen[shot_id] = (s, shot)
                continue

            # conflict
            prev_s, _prev_shot = chosen[shot_id]

            if prefer == "fail":
                print(
                    f"[FAIL] duplicate shot {shot_id} in sources "
                    f"{prev_s.get('release_id')} ({prev_s.get('src')}) and {s.get('release_id')} ({s.get('src')})"
                )
                sys.exit(1)

            # prefer latest
            if s["created_dt"] > prev_s["created_dt"]:
                print(
                    f"[WARN] duplicate {shot_id} -> picking {s.get('release_id')} (latest), ignoring {prev_s.get('release_id')}"
                )
                chosen[shot_id] = (s, shot)
            else:
                print(
                    f"[WARN] duplicate {shot_id} -> keeping {prev_s.get('release_id')} (latest or equal), ignoring {s.get('release_id')}"
                )

    # 3) copy files using source release dir + manifest path
    os.makedirs(out_root, exist_ok=False)

    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]   # tools/cli/bundle.py → repo root
    src_verify = repo_root / "tools" / "verify_bundle.py"
    dst_verify = Path(out_root) / "verify_bundle.py"

    shutil.copy2(src_verify, dst_verify)

    bundle_shots = []
    total_files = 0
    total_bytes = 0

    # stable order
    for shot_id in sorted(chosen.keys()):
        s, shot = chosen[shot_id]
        src_release_dir = s["src"]
        src_release_id = s["release_id"]

        shot_out_dir = os.path.join(out_root, shot_id)
        os.makedirs(shot_out_dir, exist_ok=True)

        out_files = []
        for fobj in shot.get("files", []):
            rel_path = fobj.get("path")  # e.g. SH041/preview.mp4
            if not rel_path:
                print(f"ERROR: file entry missing path in shot {shot_id} (source {src_release_dir})")
                sys.exit(1)

            src_file = os.path.join(src_release_dir, rel_path)
            if not os.path.exists(src_file):
                print(f"ERROR: source file missing: {src_file}")
                sys.exit(1)

            filename = os.path.basename(rel_path)
            dest_rel = f"{shot_id}/{filename}"
            dest_abs = os.path.join(out_root, dest_rel)

            shutil.copy2(src_file, dest_abs)

            size = os.path.getsize(dest_abs)
            sha = _sha256_of_file(dest_abs)

            total_files += 1
            total_bytes += size

            out_files.append({
                "key": fobj.get("key", filename),
                # keep traceability but still valid for verify:
                "source": f"{src_release_id}/{rel_path}",
                "path": dest_rel,
                "dest": dest_rel,
                "bytes": size,
                "sha256": sha,
            })

        bundle_shots.append({
            "shot_id": shot_id,
            "phase": shot.get("phase", "FAZ_1"),
            "status": shot.get("status", "DONE"),
            "files": out_files,
        })

    # 4) bundle manifest MUST match release-manifest schema style
    bundle_manifest = {
        "manifest_version": 3,
        "hash_alg": "sha256",
        "release_id": bundle_id,
        "source_durum_rel": "DURUM.json",
        "durum_sha256": "0" * 64,
        "created_utc": _utc_now_iso(),
        "totals": {
            "done_shots": len(bundle_shots),
            "files": total_files,
            "bytes": total_bytes,
        },
        "shots": bundle_shots,
        # extra info (doesn't break anything; verify-manifest should ignore unknown keys)
        "kind": "bundle",
        "sources": [
            {
                "source_release_id": s["release_id"],
                "source_manifest_sha256": s["manifest_sha256"],
                "source_path": s["src"],
                "created_utc": s["manifest"].get("created_utc"),
            }
            for s in loaded_sources
        ],
    }

    with open(os.path.join(out_root, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(bundle_manifest, f, indent=2)

    print(f"BUNDLE CREATED: {bundle_id}")


