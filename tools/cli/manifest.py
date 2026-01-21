import argparse, json, os, hashlib
from datetime import datetime, timezone

SCHEMA = "cinev4/manifest@1"
HASH_ALG = "sha256"

def _utc_now_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

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

def _collect_done_artifacts(durum: dict):
    shots = durum.get("shots", {}) or {}
    artifacts = []
    for sid, sh in shots.items():
        status = (sh or {}).get("status")
        if status != "DONE":
            continue
        outs = (sh or {}).get("outputs", {}) or {}
        # CineV3 authoritative outputs: preview.mp4 + qc.json
        for k in ("preview.mp4", "qc.json"):
            p = outs.get(k)
            if not p:
                raise SystemExit(f"[FAIL] {sid} DONE but missing outputs['{k}']")
            artifacts.append(p)
    # unique + stable order
    uniq = []
    seen = set()
    for p in artifacts:
        if p in seen:
            continue
        seen.add(p)
        uniq.append(p)
    return uniq

def main(argv=None):
    ap = argparse.ArgumentParser(prog="tools.cli manifest", add_help=True)
    ap.add_argument("durum_path", help="Path to DURUM.json (CineV3)")
    ap.add_argument("--release", required=True, help="Release id folder under releases/ (e.g. demo01_r0002)")
    ap.add_argument("--project-id", default=None, help="Override project_id (default: DURUM.active_project)")
    args = ap.parse_args(argv)

    repo_root = os.getcwd()
    durum_path = args.durum_path

    with open(durum_path, "r", encoding="utf-8") as f:
        durum = json.load(f)

    project_id = args.project_id or durum.get("active_project") or "UNKNOWN"
    rel_id = args.release.strip().replace("\\", "/").strip("/")

    rel_dir = os.path.join(repo_root, "releases", rel_id)
    os.makedirs(rel_dir, exist_ok=True)

    artifact_paths = _collect_done_artifacts(durum)

    artifacts = []
    errors = []
    for rel in artifact_paths:
        if not _is_safe_relative(rel):
            errors.append(f"BAD_PATH(not relative or escapes repo): {rel}")
            continue
        abs_path = os.path.join(repo_root, rel)
        if not os.path.isfile(abs_path):
            errors.append(f"MISSING: {rel}")
            continue

        size = os.path.getsize(abs_path)
        sha = _sha256_file(abs_path)
        artifacts.append({"path": rel.replace("\\", "/"), "size": size, "sha256": sha})

    if errors:
        print("[FAIL] manifest build failed:")
        for e in errors:
            print(" -", e)
        raise SystemExit(2)

    manifest = {
        "schema": SCHEMA,
        "project_id": project_id,
        "shot_id": "MULTI",
        "created_utc": _utc_now_z(),
        "hash_alg": HASH_ALG,
        "artifacts": artifacts,
    }

    out_path = os.path.join(rel_dir, "manifest.json")
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, out_path)

    print("[OK] manifest written:", os.path.relpath(out_path, repo_root))
    print("[OK] artifacts:", len(artifacts))

if __name__ == "__main__":
    main()
