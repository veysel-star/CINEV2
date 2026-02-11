import os
import sys
import json
import shutil
import hashlib
from datetime import datetime


def sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm_release_dir(p: str) -> str:
    # allow both "releases/ID" and "releases\\ID"
    return p.rstrip("/\\")  # no abs conversion; keep as provided


def _load_manifest(src_release_dir: str) -> tuple[dict, str, str]:
    manifest_path = os.path.join(src_release_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        print(f"ERROR: manifest not found: {manifest_path}")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    manifest_sha = sha256_of_file(manifest_path)
    release_id = manifest.get("release_id")
    if not release_id:
        print(f"ERROR: release_id missing in {manifest_path}")
        sys.exit(1)

    if manifest.get("manifest_version") != 3:
        print(f"ERROR: unsupported manifest_version in {manifest_path}: {manifest.get('manifest_version')}")
        sys.exit(1)

    return manifest, manifest_sha, release_id


def cmd_bundle(args):
    sources = args.sources
    if not sources:
        print("ERROR: --sources required")
        sys.exit(1)

    bundle_id = args.bundle_id or datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_root = os.path.join("releases", bundle_id)

    if os.path.exists(out_root):
        print(f"ERROR: output already exists: {out_root}")
        sys.exit(1)

    os.makedirs(out_root, exist_ok=False)

    # Optional: allow "--shots SH041,SH042" or "--shots SH041 SH042"
    selected_shots = None
    if getattr(args, "shots", None):
        raw = args.shots
        if len(raw) == 1 and "," in raw[0]:
            selected_shots = set(s.strip() for s in raw[0].split(",") if s.strip())
        else:
            selected_shots = set(raw)

    sources_info = []
    chosen_shots = {}  # shot_id -> (src_release_dir, src_release_id, src_manifest_sha, shot_obj)

    # 1) read each source manifest, choose shots, detect conflicts
    for src in sources:
        src = _norm_release_dir(src)
        manifest, manifest_sha, src_release_id = _load_manifest(src)

        sources_info.append({
            "source_release_id": src_release_id,
            "source_manifest_sha256": manifest_sha,
            "source_path": src
        })

        for shot in manifest.get("shots", []):
            shot_id = shot.get("shot_id")
            if not shot_id:
                print(f"ERROR: shot_id missing in manifest: {src}\\manifest.json")
                sys.exit(1)

            if selected_shots is not None and shot_id not in selected_shots:
                continue

            if shot_id in chosen_shots:
                print(f"ERROR: shot conflict detected: {shot_id}")
                sys.exit(1)

            chosen_shots[shot_id] = (src, src_release_id, manifest_sha, shot)

    # 2) copy files + build bundle shots
    total_files = 0
    total_bytes = 0
    bundle_shots = []

    for shot_id in sorted(chosen_shots.keys()):
        src_dir, src_release_id, src_manifest_sha, shot = chosen_shots[shot_id]

        out_shot_dir = os.path.join(out_root, shot_id)
        os.makedirs(out_shot_dir, exist_ok=True)

        new_files = []

        for fobj in shot.get("files", []):
            # expected fields from your release manifests:
            # key, source, path, dest, bytes, sha256
            rel_path = fobj.get("path")
            if not rel_path:
                print(f"ERROR: file.path missing for {shot_id} in {src}\\manifest.json")
                sys.exit(1)

            src_file = os.path.join(src_dir, rel_path)
            if not os.path.exists(src_file):
                print(f"ERROR: source file missing: {src_file}")
                sys.exit(1)

            # keep same dest scheme as release manifest: "SH041/preview.mp4"
            dest_rel = fobj.get("dest") or rel_path
            dest_file = os.path.join(out_root, dest_rel.replace("/", os.sep))

            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            shutil.copy2(src_file, dest_file)

            got_sha = sha256_of_file(dest_file)
            got_bytes = os.path.getsize(dest_file)

            total_files += 1
            total_bytes += got_bytes

            # keep original structure so verify-manifest remains happy
            new_files.append({
                "key": fobj.get("key"),
                "source": f"{src_release_id}:{fobj.get('source')}",
                "path": dest_rel,
                "dest": dest_rel,
                "bytes": got_bytes,
                "sha256": got_sha,
                # extra trace fields (should not break verifier if it ignores unknown keys)
                "source_release_id": src_release_id,
                "source_manifest_sha256": src_manifest_sha,
                "source_path": rel_path,
            })

        bundle_shots.append({
            "shot_id": shot_id,
            "phase": shot.get("phase"),
            "status": shot.get("status"),
            "source_release_id": src_release_id,
            "files": new_files,
        })

    bundle_manifest = {
        "manifest_version": 3,
        "hash_alg": "sha256",
        "release_id": bundle_id,
        "kind": "bundle",
        "created_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": sources_info,
        "totals": {
            "done_shots": len(bundle_shots),
            "files": total_files,
            "bytes": total_bytes
        },
        "shots": bundle_shots,
    }

    with open(os.path.join(out_root, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(bundle_manifest, f, indent=2)

    print(f"BUNDLE CREATED: {bundle_id}")

