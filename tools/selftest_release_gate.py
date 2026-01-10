import json
import subprocess
import sys
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parent.parent
CLI_RELEASE = [sys.executable, "-m", "tools.cli", "release"]

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr

def write_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def base_durum():
    return {
        "active_project": "selftest_release",
        "current_focus": "FAZ_1",
        "shots": {},
        "last_updated_utc": "2026-01-01T00:00:00Z"
    }

def add_shot(durum, sid, status, outputs):
    durum["shots"][sid] = {
        "id": sid,
        "phase": "FAZ_1",
        "status": status,
        "inputs": {"prompt": "test"},
        "outputs": outputs,
        "history": []
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
    tmp = Path(tempfile.mkdtemp())
    try:
        outdir = tmp / "releases"
        dpath = tmp / "durum.json"

        # Case 0: DONE shot outputs missing preview.mp4 key => ERR
        durum = base_durum()
        add_shot(
            durum,
            "SREL0",
            "DONE",
            {"qc.json": "outputs/v0001/qc.json"}
        )
        write_json(dpath, durum)
        rc, out = run(CLI_RELEASE + [str(dpath), "--out", str(outdir)])
        expect_error_contains("DONE requires outputs['preview.mp4']", rc, out)

        # Case 1: DONE shot has required keys but output file missing on disk => ERR
        durum = base_durum()
        add_shot(
            durum,
            "SREL1",
            "DONE",
            {"qc.json": "outputs/v0001/qc.json", "preview.mp4": "outputs/v0001/preview.mp4"}
        )
        write_json(dpath, durum)

        rc, out = run(CLI_RELEASE + [str(dpath), "--out", str(outdir)])
        expect_error_contains("file missing on disk", rc, out)

        # Case 2: files exist => OK + manifest exists and includes BOTH qc.json and preview.mp4
        (tmp / "outputs" / "v0001").mkdir(parents=True, exist_ok=True)
        (tmp / "outputs" / "v0001" / "qc.json").write_text("{}", encoding="utf-8")
        (tmp / "outputs" / "v0001" / "preview.mp4").write_text("", encoding="utf-8")

        rc, out = run(CLI_RELEASE + [str(dpath), "--out", str(outdir)])
        expect_ok(rc, out)

        rel_folders = [p for p in outdir.iterdir() if p.is_dir()]
        if not rel_folders:
            print("❌ release klasörü oluşmadı")
            sys.exit(1)

        # newest folder (by name is fine because UTC format sorts)
        rel = sorted(rel_folders)[-1]
        man = rel / "manifest.json"
        if not man.exists():
            print("❌ manifest.json bulunamadı")
            sys.exit(1)

        data = json.loads(man.read_text(encoding="utf-8"))
        # v2 manifest assertions
        if data.get("manifest_version") != 2:
            print("❌ manifest_version != 2")
            print(json.dumps(data, indent=2))
            sys.exit(1)

        sha = data.get("durum_sha256")
        if not isinstance(sha, str) or len(sha) != 64:
            print("❌ durum_sha256 invalid")
            print("durum_sha256:", sha)
            sys.exit(1)

        tot = data.get("totals", {})
        if tot.get("done_shots") != 1:
            print("❌ totals.done_shots expected 1")
            print("totals:", tot)
            sys.exit(1)

        if tot.get("files") != 2:
            print("❌ totals.files expected 2")
            print("totals:", tot)
            sys.exit(1)

        if not isinstance(tot.get("bytes"), int):
            print("❌ totals.bytes expected int")
            print("totals:", tot)
            sys.exit(1)

        if "shots" not in data or len(data["shots"]) != 1:
            print("❌ manifest içeriği beklenen değil")
            print(json.dumps(data, indent=2))
            sys.exit(1)

        files = data["shots"][0].get("files", [])
        keys = sorted([f.get("key") for f in files if isinstance(f, dict)])
        if keys != ["preview.mp4", "qc.json"]:
            print("❌ manifest files keys beklenen değil")
            print("keys:", keys)
            print(json.dumps(data, indent=2))
            sys.exit(1)

                # Case 3: manifest listed artifact paths must exist on disk
        files = data["shots"][0].get("files", [])
        for f in files:
            relpath = f.get("path")
            if not relpath:
                print("❌ manifest file entry has no path")
                sys.exit(1)

            p = (rel / relpath).resolve()
            if not p.exists():
                print("❌ manifest lists file that does not exist on disk:", relpath)
                sys.exit(1)

        # Case 4: DONE shot count matches manifest shot count
        done_shots = [
            s for s in durum["shots"].values()
            if s.get("status") == "DONE"
        ]

        if len(done_shots) != len(data.get("shots", [])):
            print("❌ DONE shot count != manifest shot count")
            print("DONE shots:", len(done_shots))
            print("manifest shots:", len(data.get("shots", [])))
            sys.exit(1)

        print("\n🎉 TÜM RELEASE GATE TESTLERİ BAŞARILI")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    main()

