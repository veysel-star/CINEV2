import hashlib
import json
import os
import sys

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def fail(msg: str, code: int = 1):
    print(f"[FAIL] {msg}")
    sys.exit(code)

def main():
    manifest_path = "manifest.json"
    if len(sys.argv) >= 2:
        manifest_path = sys.argv[1]

    if not os.path.exists(manifest_path):
        fail(f"manifest not found: {manifest_path}")

    base_dir = os.path.dirname(os.path.abspath(manifest_path)) or os.getcwd()

    with open(manifest_path, "r", encoding="utf-8") as f:
        m = json.load(f)

    files = m.get("files")
    if not isinstance(files, list) or len(files) == 0:
        # fallback: shots[*].files
        shots = m.get("shots")
        if not isinstance(shots, list) or len(shots) == 0:
            fail("manifest has no files or shots[]")

        files = []
        for sh in shots:
            sf = sh.get("files")
            if isinstance(sf, list):
                files.extend(sf)

    if not isinstance(files, list) or len(files) == 0:
        fail("manifest has no files")

    missing = 0
    bad = 0
    checked = 0

    for entry in files:
        rel = entry.get("path") or entry.get("dest")
        expected = entry.get("sha256")
        if not rel or not expected:
            fail("file entry missing path/dest/sha256")

        abs_path = os.path.join(base_dir, rel)
        if not os.path.exists(abs_path):
            print(f"[MISS] {rel}")
            missing += 1
            continue

        got = sha256_file(abs_path)
        checked += 1
        if got.lower() != expected.lower():
            print(f"[BAD]  {rel}\n       expected={expected}\n       got     ={got}")
            bad += 1

    if missing or bad:
        fail(f"verification failed: checked={checked}, missing={missing}, bad={bad}", 2)

    print(f"[OK] bundle verified: checked={checked} files")

if __name__ == "__main__":
    main()
