import json
import subprocess
import sys
import tempfile
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent
CLI = [sys.executable, "-m", "tools.cli", "listshots"]

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr

def write_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def main():
    tmp = Path(tempfile.mkdtemp())
    try:
        dpath = tmp / "durum.json"

        # minimal synthetic DURUM with known ids
        durum = {
            "active_project": "selftest_listshots",
            "current_focus": "FAZ_1",
            "shots": {
                "SH001": {
                    "id": "SH001",
                    "phase": "FAZ_1",
                    "status": "DONE",
                    "inputs": {"prompt": "p1"},
                    "outputs": {"qc.json": "outputs/v0001/qc.json", "preview.mp4": "outputs/v0001/preview.mp4"},
                    "history": []
                },
                "SH007": {
                    "id": "SH007",
                    "phase": "FAZ_1",
                    "status": "PLANNED",
                    "inputs": {"prompt": "p7"},
                    "outputs": {},
                    "history": []
                }
            },
            "last_updated_utc": "2026-01-01T00:00:00Z"
        }

        write_json(dpath, durum)

        rc, out = run(CLI + [str(dpath)])
        if rc != 0:
            print("❌ BEKLENEN OK, AMA HATA DÖNDÜ")
            print(out)
            sys.exit(1)

        # must include known ids
        if "SH001" not in out or "SH007" not in out:
            print("❌ ÇIKTIDA BEKLENEN SHOT ID'LERİ YOK")
            print(out)
            sys.exit(1)

        # must include summary
        if "TOTAL shots:" not in out or "DONE:" not in out:
            print("❌ ÖZET SATIRI YOK (TOTAL/DONE)")
            print(out)
            sys.exit(1)

        print("✅ OK")
        print("\n🎉 TÜM LISTSHOTS TESTLERİ BAŞARILI")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    main()
