import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CLI = [sys.executable, "-m", "tools.cli", "transition"]


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def write_json(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_base_durum():
    return {
        "active_project": "selftest",
        "current_focus": "FAZ_1",
        "shots": {},
        "last_updated_utc": "2026-01-01T00:00:00Z",
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
        "history": [],
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


def write_qc_json(path: Path, ok: bool, errors=None, warnings=None, note=""):
    if errors is None:
        errors = []
    if warnings is None:
        warnings = []
    payload = {
        "ok": bool(ok),
        "errors": list(errors),
        "warnings": list(warnings),
        "note": note,
        "utc": "2026-01-01T00:00:00Z",
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main():
    tmp = Path(tempfile.mkdtemp())
    try:
        # 1) IN_PROGRESS -> DONE yasak
        durum = load_base_durum()
        add_shot(durum, "S1", status="IN_PROGRESS")
        d1 = tmp / "d1.json"
        write_json(d1, durum)
        rc, out = run(CLI + [str(d1), "S1", "--to", "DONE"])
        expect_error("invalid transition", rc, out)

        # 2) outputs boşken IN_PROGRESS -> QC yasak
        durum = load_base_durum()
        add_shot(durum, "S2", status="IN_PROGRESS", outputs={})
        d2 = tmp / "d2.json"
        write_json(d2, durum)
        rc, out = run(CLI + [str(d2), "S2", "--to", "QC"])
        expect_error("requires non-empty outputs", rc, out)

        # QC dosyalarının duracağı yer
        outdir = tmp / "outputs" / "v0001"
        outdir.mkdir(parents=True, exist_ok=True)
        qc_path = outdir / "qc.json"

        # 3) QC -> DONE (qc.json key var ama dosya yok) yasak
        durum = load_base_durum()
        add_shot(
            durum,
            "S3",
            status="QC",
            outputs={"qc.json": "outputs/v0001/qc.json"},
        )
        d3 = tmp / "d3.json"
        write_json(d3, durum)

        # qc.json yokken dene
        if qc_path.exists():
            qc_path.unlink()
        rc, out = run(CLI + [str(d3), "S3", "--to", "DONE"])
        expect_error("file to exist on disk", rc, out)

        # 4) QC -> DONE (qc.json var + ok:true) OK
        # aynı state dosyası (d3) hâlâ QC’de; şimdi qc.json oluşturup dene
        write_qc_json(qc_path, ok=True, errors=[], warnings=[], note="selftest pass")
        rc, out = run(CLI + [str(d3), "S3", "--to", "DONE"])
        expect_ok(rc, out)

        # 5) QC -> DONE (qc.json var ama ok:false) yasak
        # NOT: d3 artık DONE’a geçtiği için yeni bir durum dosyası oluşturuyoruz.
        durum = load_base_durum()
        add_shot(
            durum,
            "S5",
            status="QC",
            outputs={"qc.json": "outputs/v0001/qc.json"},
        )
        d5 = tmp / "d5.json"
        write_json(d5, durum)

        write_qc_json(
            qc_path,
            ok=False,
            errors=["missing preview.mp4"],
            warnings=[],
            note="selftest fail",
        )
        rc, out = run(CLI + [str(d5), "S5", "--to", "DONE"])
        expect_error("requires qc.json ok:true", rc, out)

        print("\n🎉 TÜM QC GATE TESTLERİ BAŞARILI")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()

