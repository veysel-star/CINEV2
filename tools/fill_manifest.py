import json, os, hashlib

manifest_path = r"releases/demo01_r0001/manifest.json"
root = os.getcwd()

def sha256_file(fp: str) -> str:
    h = hashlib.sha256()
    with open(fp, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

with open(manifest_path, "r", encoding="utf-8") as f:
    m = json.load(f)

errors = []
for a in m.get("artifacts", []):
    rel = a["path"]
    abs_path = os.path.join(root, rel)
    if not os.path.isfile(abs_path):
        errors.append(f"MISSING: {rel}")
        continue
    a["size"] = os.path.getsize(abs_path)
    a["sha256"] = sha256_file(abs_path)

if errors:
    print("[FAIL] Missing artifacts:")
    for e in errors:
        print(" -", e)
    raise SystemExit(2)

tmp = manifest_path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(m, f, ensure_ascii=False, indent=2)
    f.write("\n")

os.replace(tmp, manifest_path)
print("[OK] manifest filled:", manifest_path)
