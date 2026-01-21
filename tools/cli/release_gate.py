import argparse, json, os, sys

def _read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _is_safe_relative(path: str) -> bool:
    if os.path.isabs(path):
        return False
    norm = os.path.normpath(path).replace("\\", "/")
    if norm.startswith("../") or norm == "..":
        return False
    return True

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

    # call verify-manifest (already in CLI) via module import (no subprocess)
    from .verify_manifest import main as verify_manifest
    verify_manifest([manifest_path])

    print("[OK] release gate passed:", args.release)

if __name__ == "__main__":
    main()
