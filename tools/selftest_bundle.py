import os
import sys
import shutil
import subprocess
from pathlib import Path
import json
import hashlib
from datetime import datetime, timezone



ROOT = Path(__file__).resolve().parent.parent
RELEASES = ROOT / "releases"
TMP_ROOT = ROOT / ".tmp_bundle_selftest"


SRC_1 = "R1"
SRC_2 = "R2"
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

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_file(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def make_fake_release(base: Path, release_id: str, shot_id: str):
    """
    base: TMP_ROOT
    Creates:
      base/releases/<release_id>/<shot_id>/preview.mp4
      base/releases/<release_id>/<shot_id>/qc.json
      base/releases/<release_id>/manifest.json
    """
    rel_dir = base / "releases" / release_id
    shot_dir = rel_dir / shot_id
    shot_dir.mkdir(parents=True, exist_ok=True)

    preview_bytes = b"FAKE_MP4_BYTES\n" + release_id.encode("utf-8") + b"\n" + shot_id.encode("utf-8") + b"\n"
    qc_obj = {"ok": True, "shot_id": shot_id, "release_id": release_id}
    qc_bytes = (json.dumps(qc_obj, indent=2) + "\n").encode("utf-8")

    preview_rel = f"{shot_id}/preview.mp4"
    qc_rel = f"{shot_id}/qc.json"

    write_file(rel_dir / preview_rel, preview_bytes)
    write_file(rel_dir / qc_rel, qc_bytes)

    preview_sha = sha256_bytes(preview_bytes)
    qc_sha = sha256_bytes(qc_bytes)

    manifest = {
        "manifest_version": 3,
        "hash_alg": "sha256",
        "release_id": release_id,
        "source_durum_rel": "DURUM.json",
        "durum_sha256": "0" * 64,
        "created_utc": utc_now_iso(),
        "totals": {
            "done_shots": 1,
            "files": 2,
            "bytes": len(preview_bytes) + len(qc_bytes),
        },
        "shots": [
            {
                "shot_id": shot_id,
                "phase": "FAZ_1",
                "status": "DONE",
                "files": [
                    {
                        "key": "preview.mp4",
                        "source": preview_rel,
                        "path": preview_rel,
                        "dest": preview_rel,
                        "bytes": len(preview_bytes),
                        "sha256": preview_sha,
                    },
                    {
                        "key": "qc.json",
                        "source": qc_rel,
                        "path": qc_rel,
                        "dest": qc_rel,
                        "bytes": len(qc_bytes),
                        "sha256": qc_sha,
                    },
                ],
            }
        ],
    }

    (rel_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


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

    # Create 2 fake source releases inside temp (CI-safe)
    make_fake_release(TMP_ROOT, SRC_1, "SH041")
    make_fake_release(TMP_ROOT, SRC_2, "SH042")


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
