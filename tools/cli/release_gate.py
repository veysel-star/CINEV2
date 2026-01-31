import argparse, json, os, sys, hashlib
from pathlib import Path

HASH_ALG = "sha256"

def _enforce_qc_rules(qc_paths):
    """
    Second lock:
    - qc.json must be ok:true
    - if metrics.character_passive_status exists => must be PASSIVE_OK
      (FAZ_2 için asıl kilit bu; metrik yoksa bu kontrol devreye girmez)
    """
    errs = []
    for p in qc_paths:
        try:
            qc = json.loads(Path(p).read_text(encoding="utf-8"))
        except Exception as e:
            errs.append(f"qc.json read/parse failed: {p} ({e})")
            continue

        if not isinstance(qc, dict):
            errs.append(f"qc.json must be object: {p}")
            continue

        if qc.get("ok") is not True:
            errs.append(f"qc.json must be ok:true: {p}")
            continue

        metrics = qc.get("metrics", {})
        if isinstance(metrics, dict) and "character_passive_status" in metrics:
            if metrics.get("character_passive_status") != "PASSIVE_OK":
                errs.append(f"character_passive_status must be PASSIVE_OK: {p}")

    return errs


def _read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

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

def _verify_cinev3_manifest_v3(manifest: dict, base_dir_abs: str):
    # NOTE: v3 paths are relative to the release folder (where manifest.json lives).
    if manifest.get("manifest_version") != 3:
        print("[FAIL] unsupported manifest_version:", manifest.get("manifest_version"))
        sys.exit(2)

    shots = manifest.get("shots")
    if not isinstance(shots, list) or len(shots) == 0:
        print("[FAIL] manifest v3: shots must be a non-empty list")
        sys.exit(2)

    errors = []
    checked = 0

    # --- FAZ_2 QC hard gate (release-level) ---
    for sh in shots:
        if sh.get("phase") != "FAZ_2":
            continue

        files = (sh or {}).get("files")
        if not isinstance(files, list):
            print(f"[FAIL] FAZ_2 shot {sh.get('shot_id')} missing files list in manifest")
            sys.exit(2)

        # qc.json'u files[] içinden bul
        qc_rel = None
        for f in files:
            rel = (f or {}).get("path", "")
            if not isinstance(rel, str) or not rel.strip():
                continue
            # hem "outputs/vXXXX/qc.json" hem "outputs\\vXXXX\\qc.json" toleransı
            rel_norm = rel.replace("\\", "/")
            if rel_norm.endswith("/qc.json") or rel_norm.endswith("qc.json"):
                qc_rel = rel
                break

        if not isinstance(qc_rel, str) or not qc_rel.strip():
            print(f"[FAIL] FAZ_2 shot {sh.get('shot_id')} missing qc.json reference (not present in files[])")
            sys.exit(2)

        if not _is_safe_relative(qc_rel):
            print(f"[FAIL] FAZ_2 shot {sh.get('shot_id')} qc.json path is unsafe: {qc_rel}")
            sys.exit(2)

        qc_abs = os.path.join(base_dir_abs, qc_rel)
        if not os.path.isfile(qc_abs):
            print(f"[FAIL] FAZ_2 shot {sh.get('shot_id')} qc.json not found on disk: {qc_rel}")
            sys.exit(2)

        try:
            with open(qc_abs, "r", encoding="utf-8") as fp:
                qc_data = json.load(fp)
        except Exception as e:
            print(f"[FAIL] FAZ_2 shot {sh.get('shot_id')} qc.json invalid JSON: {e}")
            sys.exit(2)

        # qc PASS zorunlu
        if qc_data.get("ok") is not True:
            print(f"[FAIL] FAZ_2 shot {sh.get('shot_id')} qc.json must be ok:true")
            sys.exit(2)

        if qc_data.get("errors") not in (None, [], ()):
            print(f"[FAIL] FAZ_2 shot {sh.get('shot_id')} qc.json errors must be []")
            sys.exit(2)

        # PASSIVE_OK zorunlu
        if (qc_data.get("metrics") or {}).get("character_passive_status") != "PASSIVE_OK":
            print(
                f"[FAIL] FAZ_2 shot {sh.get('shot_id')} "
                f"requires character_passive_status == PASSIVE_OK"
            )
            sys.exit(2)

    for sh in shots:
        files = (sh or {}).get("files")
        if not isinstance(files, list):
            errors.append(f"BAD_SHOT_FILES: {sh.get('shot_id')}")
            continue

        for f in files:
            rel = (f or {}).get("path", "")
            if not isinstance(rel, str) or rel.strip() == "":
                errors.append("BAD_PATH: <empty>")
                continue
            if not _is_safe_relative(rel):
                errors.append(f"BAD_PATH: {rel}")
                continue

            abs_path = os.path.join(base_dir_abs, rel)
            if not os.path.isfile(abs_path):
                errors.append(f"MISSING: {rel}")
                continue

            size_disk = os.path.getsize(abs_path)
            size_manifest = f.get("bytes")
            if size_manifest != size_disk:
                errors.append(f"SIZE_MISMATCH: {rel} manifest={size_manifest} disk={size_disk}")

            sha_disk = _sha256_file(abs_path)
            if sha_disk != f.get("sha256"):
                errors.append(f"SHA_MISMATCH: {rel}")

            checked += 1

    if errors:
        print("[FAIL] manifest v3 verify failed:")
        for e in errors:
            print(" -", e)
        sys.exit(2)

    print("[OK] manifest v3 verify passed. files:", checked)

def main(argv=None):
    ap = argparse.ArgumentParser(prog="tools.cli release-gate", add_help=True)
    ap.add_argument("--project", required=True, help="Project id (e.g. demo01)")
    ap.add_argument("--release", required=True, help="Release id (e.g. demo01_r0002)")
    ap.add_argument("--project-file", default=None, help="Override project.json path")
    ap.add_argument("--manifest", default=None, help="Override manifest.json path")
    args = ap.parse_args(argv)

    repo_root = os.getcwd()

    project_path = args.project_file or os.path.join("projects", args.project, "project.json")
    manifest_path = args.manifest or os.path.join("releases", args.release, "manifest.json")

    if not _is_safe_relative(project_path):
        print("[FAIL] BAD_PROJECT_PATH:", project_path)
        sys.exit(2)
    if not _is_safe_relative(manifest_path):
        print("[FAIL] BAD_MANIFEST_PATH:", manifest_path)
        sys.exit(2)

    project_abs = os.path.join(repo_root, project_path)
    manifest_abs = os.path.join(repo_root, manifest_path)

    if not os.path.isfile(project_abs):
        print("[FAIL] project.json missing:", project_path)
        sys.exit(2)
    if not os.path.isfile(manifest_abs):
        print("[FAIL] manifest.json missing:", manifest_path)
        sys.exit(2)

    proj = _read_json(project_abs)
    pol = (proj.get("policy") or {})

    if pol.get("hash_alg") != "sha256":
        print("[FAIL] policy.hash_alg must be sha256")
        sys.exit(2)
    if pol.get("path_mode") != "relative":
        print("[FAIL] policy.path_mode must be relative")
        sys.exit(2)
    if pol.get("immutable_outputs") is not True:
        print("[FAIL] policy.immutable_outputs must be true")
        sys.exit(2)
    if pol.get("done_requires_manifest") is not True:
        print("[FAIL] policy.done_requires_manifest must be true")
        sys.exit(2)

    m = _read_json(manifest_abs)

    # CineV4 manifest@1: artifacts are repo-relative
    if "hash_alg" in m:
        if m.get("hash_alg") != HASH_ALG:
            print("[FAIL] unsupported hash_alg:", m.get("hash_alg"))
            sys.exit(2)
        from .verify_manifest import main as verify_manifest
        verify_manifest([manifest_path])
        print("[OK] release gate passed:", args.release)
        return

    # CineV3 manifest v3: paths are release-folder-relative
    if m.get("manifest_version") == 3:
        base_dir_abs = os.path.dirname(manifest_abs)
        _verify_cinev3_manifest_v3(m, base_dir_abs)
        print("[OK] release gate passed:", args.release)
        return

    print("[FAIL] unknown manifest format (no hash_alg, no manifest_version=3)")
    sys.exit(2)

if __name__ == "__main__":
    main()
