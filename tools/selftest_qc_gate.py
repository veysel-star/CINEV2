import json
import subprocess
import sys
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parent.parent
CLI = [sys.executable, "-m", "tools.cli", "transition"]

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr

def write_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def load_base_durum():
    return {
        "active_project": "selftest",
        "current_focus": "FAZ_1",
        "shots": {},
        "last_updated_utc": "2026-01-01T00:00:00Z"
    }

def add_shot(durum, sid, status="PLANNED", outputs=None):
    if outputs is None:
        outputs = {}
    durum["shots"][sid] = {
        "id": sid,
        "phase": "FAZ_1",
        "status": status,
        "inputs": {"prompt": "test"},
        "outputs": outputs,
        "history": []
    }

def expect_error(msg, rc, out):
    if rc == 0:
        print("❌ BEKLENEN HATA, AMA OK DÖNDÜ")
        print(out)
        sys.exit(1)
    if msg not in out:
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
        durum = load_base_durum()

        # 1) IN_PROGRESS -> DONE yasak
        add_shot(durum, "S1", status="IN_PROGRESS")
        dpath = tmp / "d1.json"
        write_json(dpath, durum)
        rc, out = run(CLI + [str(dpath), "S1", "--to", "DONE"])
        expect_error("invalid transition", rc, out)

        # 2) outputs boşken IN_PROGRESS -> QC yasak
        add_shot(durum, "S2", status="IN_PROGRESS", outputs={})
        dpath = tmp / "d2.json"
        write_json(dpath, durum)
        rc, out = run(CLI + [str(dpath), "S2", "--to", "QC"])
        expect_error("requires non-empty outputs", rc, out)

        # 3) QC -> DONE (qc.json key var ama dosya yok) yasak
        add_shot(
            durum,
            "S3",
            status="QC",
            outputs={"qc.json": "outputs/v0001/qc.json"}
        )
        dpath = tmp / "d3.json"
        write_json(dpath, durum)
        rc, out = run(CLI + [str(dpath), "S3", "--to", "DONE"])
        expect_error("file to exist on disk", rc, out)

        # 4) QC -> DONE (qc.json key var + dosya var) OK
        outdir = tmp / "outputs" / "v0001"
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "qc.json").write_text("{}", encoding="utf-8")

        rc, out = run(CLI + [str(dpath), "S3", "--to", "DONE"])
        expect_ok(rc, out)

        print("\n🎉 TÜM QC GATE TESTLERİ BAŞARILI")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    main()
