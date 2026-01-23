import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent  # repo root (CINEV2)
CLI_RELEASE = [sys.executable, "-m", "tools.cli", "release"]
CLI_GATE = [sys.executable, "-m", "tools.cli", "release-gate"]


def run(cmd, cwd: Path):
    """
    Run CLI in an isolated temp working dir while still importing repo's 'tools' package.
    """
    env = os.environ.copy()

    # Ensure 'python -m tools.cli ...' can import from the repo root
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + prev if prev else "")

    p = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=env,
    )
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def write_json(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def base_durum():
    return {
        "active_project": "selftest_release",
        "current_focus": "FAZ_1",
        "shots": {},
        "last_updated_utc": "2026-01-01T00:00:00Z",
    }


def add_shot(durum, sid, status, outputs):
    durum["shots"][sid] = {
        "id": sid,
        "phase": "FAZ_1",
        "status": status,
        "inputs": {"prompt": "test"},
        "outputs": outputs,
        "history": [],
    }


def expect_error_contains(expected, rc, out):
    if rc == 0:
        print("❌ BEKLENEN HATA, AMA OK DÖNDÜ")
        print(out)
        sys.exit(1)
    if expected not in out:
        print("❌ HATA VAR AMA MESAJ FARKLI")
        print(out)
        sys.exit(1)
    print("✅ OK (beklenen hata)")


def expect_ok(rc, out):
    if rc != 0:
        print("❌ BEKLENEN OK, AMA HATA DÖNDÜ")
        print(out)
        sys.exit(1)
    print("✅ OK")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="cinev2_selftest_release_gate_"))
    try:
        # Everything happens inside tmp (relative paths become stable)
        dpath = tmp / "durum.json"
        outdir = tmp / "releases"

        # Create minimal project.json that release-gate expects (inside tmp!)
        proj_dir = tmp / "projects" / "selftest_release"
        proj_dir.mkdir(parents=True, exist_ok=True)
        project_file = proj_dir / "project.json"
        write_json(
            project_file,
            {
                "id": "selftest_release",
                "policy": {
                    "hash_alg": "sha256",
                    "path_mode": "relative",
                    "immutable_outputs": True,
                    "done_requires_manifest": True,
                },
            },
        )

        # ----------------------------
        # Case 0: DONE shot outputs missing preview.mp4 key => ERR
        durum = base_durum()
        add_shot(durum, "SREL0", "DONE", {"qc.json": "outputs/v0001/qc.json"})
        write_json(dpath, durum)

        rc, out = run(
            CLI_RELEASE
            + [
                "durum.json",
                "--out",
                "releases",
                "--release-id",
                "selftest_bad0",
                "--project",
                "selftest_release",
            ],
            cwd=tmp,
        )
        expect_error_contains("DONE requires outputs['preview.mp4']", rc, out)

        # ----------------------------
        # Case 1: DONE shot has required keys but output file missing on disk => ERR
        durum = base_durum()
        add_shot(
            durum,
            "SREL1",
            "DONE",
            {"qc.json": "outputs/v0001/qc.json", "preview.mp4": "outputs/v0001/preview.mp4"},
        )
        write_json(dpath, durum)

        rc, out = run(
            CLI_RELEASE
            + [
                "durum.json",
                "--out",
                "releases",
                "--release-id",
                "selftest_bad1",
                "--project",
                "selftest_release",
            ],
            cwd=tmp,
        )
        expect_error_contains("file missing on disk", rc, out)

        # ----------------------------
        # Case 2: files exist => OK + manifest exists; then release-gate should pass
        (tmp / "outputs" / "v0001").mkdir(parents=True, exist_ok=True)
        (tmp / "outputs" / "v0001" / "qc.json").write_text("{}", encoding="utf-8")
        (tmp / "outputs" / "v0001" / "preview.mp4").write_text("", encoding="utf-8")

        durum = base_durum()
        add_shot(
            durum,
            "SREL2",
            "DONE",
            {"qc.json": "outputs/v0001/qc.json", "preview.mp4": "outputs/v0001/preview.mp4"},
        )
        write_json(dpath, durum)

        rel_id = "selftest_r0001"
        rc, out = run(
            CLI_RELEASE
            + [
                "durum.json",
                "--out",
                "releases",
                "--release-id",
                rel_id,
                "--project",
                "selftest_release",
            ],
            cwd=tmp,
        )
        expect_ok(rc, out)

        # Deterministic manifest path (NO folder guessing)
        rel = tmp / "releases" / rel_id
        man = rel / "manifest.json"
        if not rel.exists():
            print("❌ release klasörü oluşmadı:", str(rel))
            sys.exit(1)
        if not man.exists():
            print("❌ manifest.json bulunamadı:", str(man))
            sys.exit(1)

        # Run release-gate against the manifest we just created
        rc, out = run(
            CLI_GATE
            + [
                "--project",
                "selftest_release",
                "--release",
                rel_id,
                "--project-file",
                str(project_file.relative_to(tmp)),
                "--manifest",
                str(man.relative_to(tmp)),
            ],
            cwd=tmp,
        )
        expect_ok(rc, out)

        # Extra sanity: manifest should list correct number of DONE shots (=1 here)
        data = json.loads(man.read_text(encoding="utf-8"))
        done_shots = [s for s in durum["shots"].values() if s.get("status") == "DONE"]
        if len(done_shots) != len(data.get("shots", [])):
            print("❌ DONE shot count != manifest shot count")
            print("DONE shots:", len(done_shots))
            print("manifest shots:", len(data.get("shots", [])))
            sys.exit(1)

        print("\n🎉 TÜM RELEASE GATE TESTLERİ BAŞARILI")
        return 0

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())




