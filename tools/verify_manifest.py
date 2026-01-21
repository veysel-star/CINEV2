import json, os, hashlib, sys

manifest_path = r"releases/demo01_r0001/manifest.json"
root = os.getcwd()

def sha256_file(fp: str) -> str:
    h = hashlib.sha256()
    with open(fp, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

m = json.load(open(manifest_path, "r", encoding="utf-8"))

errors = []
for a in m.get("artifacts", []):
    rel = a["path"]
    abs_path = os.path.join(root, rel)
    if not os.path.isfile(abs_path):
        errors.append(f"MISSING: {rel}")
        continue

    size_disk = os.path.getsize(abs_path)
    if size_disk != a.get("size"):
        errors.append(f"SIZE_MISMATCH: {rel} manifest={a.get('size')} disk={size_disk}")

    sha_disk = sha256_file(abs_path)
    if sha_disk != a.get("sha256"):
        errors.append(f"SHA_MISMATCH: {rel}")

if errors:
    print("[FAIL] manifest verify failed:")
    for e in errors:
        print(" -", e)
    sys.exit(2)

print("[OK] manifest verify passed:", manifest_path)
