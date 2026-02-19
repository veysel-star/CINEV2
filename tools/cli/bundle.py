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

        # hard requirements (v4 ONLY)
        if m.get("manifest_version") != 4:
            print(f"ERROR: unsupported manifest_version in {manifest_path}: {m.get('manifest_version')}")
            sys.exit(1)

        hash_alg = m.get("hash_alg")
        if hash_alg != "sha256":
            print(f"ERROR: hash_alg must be sha256 in {manifest_path}")
            sys.exit(1)

        created_utc = m.get("created_utc")
        if not created_utc:
            print(f"ERROR: created_utc missing in {manifest_path}")
            sys.exit(1)

        release_id = m.get("release_id")
        if not release_id:
            print(f"ERROR: release_id missing in {manifest_path}")
            sys.exit(1)

        loaded_sources.append({
            "src": src,
            "manifest_path": manifest_path,
            "manifest": m,
            "release_id": release_id,
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

    # 3) create bundle release dir + copy files
    os.makedirs(out_root, exist_ok=False)

    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[2]  # tools/cli/bundle.py → repo root

    # keep verify script inside bundle for convenience
    src_verify = repo_root / "tools" / "verify_bundle.py"
    dst_verify = Path(out_root) / "verify_bundle.py"
    if src_verify.exists():
        shutil.copy2(src_verify, dst_verify)

    bundle_shots = []
    bundle_artifacts = []

    total_files = 0
    total_bytes = 0

    # stable order
    for shot_id in sorted(chosen.keys()):
        s, shot = chosen[shot_id]
        src_release_dir = s["src"]
        src_release_id = s["release_id"]

        # create shot dir
        shot_out_dir = os.path.join(out_root, shot_id)
        os.makedirs(shot_out_dir, exist_ok=True)

        out_files = []
        out_artifacts = []

        prefix = f"releases/{src_release_id}/"

        # v4: source files come from artifacts (repo-relative)
        for a in s["manifest"].get("artifacts", []):
            rel_path = a.get("path")  # e.g. releases/R1/SH041/preview.mp4
            if not rel_path:
                print(f"ERROR: artifact missing path in source {src_release_dir}")
                sys.exit(1)

            if not rel_path.startswith(prefix):
                print(f"ERROR: artifact path not under {prefix}: {rel_path}")
                sys.exit(1)

            suffix = rel_path[len(prefix):]  # SH041/preview.mp4
            art_shot = suffix.split("/", 1)[0]
            if art_shot != shot_id:
                continue

            src_file = os.path.join(src_release_dir, suffix)
            if not os.path.exists(src_file):
                print(f"ERROR: source file missing: {src_file}")
                sys.exit(1)

            filename = os.path.basename(suffix)
            dest_rel = f"{shot_id}/{filename}"
            dest_abs = os.path.join(out_root, dest_rel)

            shutil.copy2(src_file, dest_abs)

            size = os.path.getsize(dest_abs)
            sha = _sha256_of_file(dest_abs)

            total_files += 1
            total_bytes += size

            out_files.append({
                "key": filename,
                "source": rel_path,
                "path": dest_rel,
                "dest": dest_rel,
                "bytes": size,
                "sha256": sha,
            })

            out_artifacts.append({
                "path": f"releases/{bundle_id}/{dest_rel}",
                "size": size,
                "sha256": sha,
            })

        # record this shot in bundle (even if files empty, it will likely fail verify later)
        bundle_shots.append({
            "shot_id": shot_id,
            "phase": shot.get("phase"),
            "status": shot.get("status"),
            "files": out_files,
        })
        bundle_artifacts.extend(out_artifacts)

    # 4) write bundle manifest (v4 strict)
    bundle_manifest = {
        "manifest_version": 4,
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
        "shots": bundle_shots,          # harmless; v4 verify uses artifacts
        "artifacts": bundle_artifacts,  # REQUIRED in v4 strict
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


