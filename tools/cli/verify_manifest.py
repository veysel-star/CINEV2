import argparse, json, os, hashlib, sys

HASH_ALG = "sha256"
MANIFEST_VERSION = 4


def _sha256_file(fp: str) -> str:
    h = hashlib.sha256()
    with open(fp, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_safe_relative(path: str) -> bool:
    if os.path.isabs(path):
        return False
    norm = os.path.normpath(path).replace("\\", "/")
    if norm.startswith("../") or norm == "..":
        return False
    return True


def _fail(msg: str):
    print(f"[FAIL] {msg}")
    sys.exit(2)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tools.cli verify-manifest", add_help=True)
    ap.add_argument("manifest_path", help="Path to manifest.json")
    args = ap.parse_args(argv)

    repo_root = os.getcwd()
    mp = args.manifest_path
    m = json.load(open(mp, "r", encoding="utf-8"))

    # ---- v4 strict header ----
    if m.get("manifest_version") != MANIFEST_VERSION:
        _fail(f"manifest_version must be {MANIFEST_VERSION} (got {m.get('manifest_version')})")

    hash_alg = m.get("hash_alg")
    if not hash_alg:
        _fail("hash_alg is required (no backward compatibility)")

    if hash_alg != HASH_ALG:
        _fail(f"unsupported hash_alg: {hash_alg} (only {HASH_ALG} allowed)")

    artifacts = m.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) == 0:
        _fail("artifacts must be a non-empty list (v4 strict)")

    errors = []

    for a in artifacts:
        if not isinstance(a, dict):
            errors.append("BAD_ARTIFACT: not an object")
            continue

        rel = a.get("path")
        if not isinstance(rel, str) or not rel.strip():
            errors.append("BAD_PATH: <empty>")
            continue

        if not _is_safe_relative(rel):
            errors.append(f"BAD_PATH: {rel}")
            continue

        abs_path = os.path.join(repo_root, rel)
        if not os.path.isfile(abs_path):
            errors.append(f"MISSING: {rel}")
            continue

        size_disk = os.path.getsize(abs_path)
        if size_disk != a.get("size"):
            errors.append(f"SIZE_MISMATCH: {rel} manifest={a.get('size')} disk={size_disk}")

        sha_disk = _sha256_file(abs_path)
        if sha_disk != a.get("sha256"):
            errors.append(f"SHA_MISMATCH: {rel}")

    if errors:
        print("[FAIL] manifest verify failed:")
        for e in errors:
            print(" -", e)
        sys.exit(2)

    print("[OK] manifest verify passed:", mp)


if __name__ == "__main__":
    main()

