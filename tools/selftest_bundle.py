import os
import sys
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RELEASES = ROOT / "releases"
TMP_ROOT = ROOT / ".tmp_bundle_selftest"


SRC_1 = "20260210T194046Z"
SRC_2 = "20260211T165939Z"
BUNDLE_ID = "SELFTEST_BUNDLE_01"
PROJECT_ID = "demo01"


def run(cmd, cwd=None):
    print(f"[RUN] {' '.join(cmd)}")

    env = os.environ.copy()
    root_str = str(ROOT)

    sep = ";" if os.name == "nt" else ":"
    if env.get("PYTHONPATH"):
        env["PYTHONPATH"] = root_str + sep + env["PYTHONPATH"]
    else:
        env["PYTHONPATH"] = root_str

    result = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    print(result.stdout)

    if result.returncode != 0:
        print("[FAIL] command failed")
        sys.exit(1)

def main():
    print("=== BUNDLE SELFTEST START ===")

    if TMP_ROOT.exists():
        shutil.rmtree(TMP_ROOT)

    TMP_ROOT.mkdir(parents=True)
    tmp_releases = TMP_ROOT / "releases"
    tmp_releases.mkdir()

    # copy project config into temp (release-gate needs it)
    src_project_dir = ROOT / "projects" / PROJECT_ID
    dst_project_dir = TMP_ROOT / "projects" / PROJECT_ID
    if not src_project_dir.exists():
        print(f"[FAIL] project dir not found: {src_project_dir}")
        sys.exit(1)
    dst_project_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_project_dir, dst_project_dir)

    # copy source releases into temp
    for src in [SRC_1, SRC_2]:
        src_path = RELEASES / src
        if not src_path.exists():
            print(f"[FAIL] source release not found: {src}")
            sys.exit(1)

        shutil.copytree(src_path, tmp_releases / src)

    # run bundle
    run([
        sys.executable, "-m", "tools.cli", "bundle",
        "--sources",
        f"releases/{SRC_1}",
        f"releases/{SRC_2}",
        "--bundle-id", BUNDLE_ID
    ], cwd=TMP_ROOT)

    manifest_path = tmp_releases / BUNDLE_ID / "manifest.json"

    if not manifest_path.exists():
        print("[FAIL] bundle manifest not created")
        sys.exit(1)

    # verify manifest
    run([
        sys.executable, "-m", "tools.cli", "verify-manifest",
        f"releases/{BUNDLE_ID}/manifest.json"
    ], cwd=TMP_ROOT)

    # release gate
    run([
        sys.executable, "-m", "tools.cli", "release-gate",
        "--project", PROJECT_ID,
        "--release", BUNDLE_ID
    ], cwd=TMP_ROOT)

    print("=== BUNDLE SELFTEST PASS ===")

    shutil.rmtree(TMP_ROOT)


if __name__ == "__main__":
    main()
