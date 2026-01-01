import json
import subprocess
import sys
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parent.parent
CLI_RELEASE = [sys.executable, "-m", "tools.cli", "release"]
CLI_TRANSITION = [sys.executable, "-m", "tools.cli", "transition"]

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
        # Case 1: DONE shot exists but output file missing => ERR
        durum = base_durum()
        add_shot(
            durum,
            "SREL1",
            "DONE",
            {"qc.json": "outputs/v0001/qc.json", "preview.mp4": "outputs/v0001/preview.mp4"}
        )
        dpath = tmp / "durum.json"
        write_json(dpath, durum)

        outdir = tmp / "releases"
        rc, out = run(CLI_RELEASE + [str(dpath), "--out", str(outdir)])
        expect_error_contains("file missing on disk", rc, out)

        # Case 2: files exist => OK + manifest exists
        (tmp / "outputs" / "v0001").mkdir(parents=True, exist_ok=True)
        (tmp / "outputs" / "v0001" / "qc.json").write_text("{}", encoding="utf-8")
        (tmp / "outputs" / "v0001" / "preview.mp4").write_text("", encoding="utf-8")

        rc, out = run(CLI_RELEASE + [str(dpath), "--out", str(outdir)])
        expect_ok(rc, out)

        # Find the created release folder and check manifest
        rel_folders = [p for p in outdir.iterdir() if p.is_dir()]
        if not rel_folders:
            print("❌ release klasörü oluşmadı")
            sys.exit(1)

        # newest folder
        rel = sorted(rel_folders)[-1]
        man = rel / "manifest.json"
        if not man.exists():
            print("❌ manifest.json bulunamadı")
            sys.exit(1)

        data = json.loads(man.read_text(encoding="utf-8"))
        if "shots" not in data or len(data["shots"]) != 1:
            print("❌ manifest içeriği beklenen değil")
            print(json.dumps(data, indent=2))
            sys.exit(1)

        print("\n🎉 TÜM RELEASE GATE TESTLERİ BAŞARILI")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    main()
