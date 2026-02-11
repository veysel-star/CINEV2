import os
import sys
import json
import shutil
import hashlib
from datetime import datetime


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_bundle(args):
    sources = args.sources
    if not sources or len(sources) < 1:
        print("ERROR: at least one --source required")
        sys.exit(1)

    bundle_id = args.bundle_id or datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_root = os.path.join("releases", bundle_id)

    if os.path.exists(out_root):
        print(f"ERROR: release {bundle_id} already exists")
        sys.exit(1)

    os.makedirs(out_root)

    all_shots = {}
    sources_info = []

    for src in sources:
        manifest_path = os.path.join(src, "manifest.json")
        if not os.path.exists(manifest_path):
            print(f"ERROR: manifest not found in {src}")
            sys.exit(1)

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        manifest_hash = sha256_of_file(manifest_path)

        sources_info.append({
            "source_release_id": manifest.get("release_id"),
            "source_manifest_sha256": manifest_hash,
            "source_path": src
        })

        for shot in manifest.get("shots", []):
            shot_id = shot["shot_id"]
            if shot_id in all_shots:
                print(f"ERROR: shot conflict detected: {shot_id}")
                sys.exit(1)

            all_shots[shot_id] = {
                "source_release_id": manifest.get("release_id"),
                "files": shot.get("files", [])
            }

    total_files = 0
    total_bytes = 0
    bundle_shots = []

    for shot_id, data in all_shots.items():
        src_release = data["source_release_id"]
        shot_dir = os.path.join(out_root, shot_id)
        os.makedirs(shot_dir)

        new_files = []

        for file_entry in data["files"]:
            src_path = file_entry["path"]
            filename = os.path.basename(src_path)
            dest_path = os.path.join(shot_dir, filename)

            shutil.copy2(src_path, dest_path)

            file_hash = sha256_of_file(dest_path)
            file_size = os.path.getsize(dest_path)

            total_files += 1
            total_bytes += file_size

            new_files.append({
                "name": filename,
                "sha256": file_hash,
                "bytes": file_size
            })

        bundle_shots.append({
            "shot_id": shot_id,
            "source_release_id": src_release,
            "files": new_files
        })

    bundle_manifest = {
        "manifest_version": 3,
        "release_id": bundle_id,
        "kind": "bundle",
        "sources": sources_info,
        "shots": bundle_shots,
        "totals": {
            "total_shots": len(bundle_shots),
            "total_files": total_files,
            "total_bytes": total_bytes
        }
    }

    with open(os.path.join(out_root, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(bundle_manifest, f, indent=2)

    print(f"BUNDLE CREATED: {bundle_id}")
