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

    # Şimdilik minimal manifest (formatı bir sonraki adımda release manifestine birebir uyarlayacağız)
    bundle_manifest = {
        "manifest_version": 3,
        "hash_alg": "sha256",
        "release_id": bundle_id,
        "kind": "bundle",
        "sources": [],
        "shots": [],
        "totals": {"total_shots": 0, "total_files": 0, "total_bytes": 0},
    }

    with open(os.path.join(out_root, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(bundle_manifest, f, indent=2)

    print(f"BUNDLE CREATED: {bundle_id}")
