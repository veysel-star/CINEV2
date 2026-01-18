# tools/selftest_cinev3_contract.py
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "tools.cli", *args],
        text=True,
        capture_output=True,
    )


def ok(name: str) -> None:
    print(f"✅ {name}: OK")


def fail(name: str, r: subprocess.CompletedProcess) -> int:
    print(f"❌ {name}: FAIL")
    if r.stdout:
        print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="")
    return 1


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "outputs" / "v0001").mkdir(parents=True, exist_ok=True)

        durum_path = root / "DURUM_v3.json"
        preview_path = root / "outputs" / "v0001" / "preview.mp4"
        qc_path = root / "outputs" / "v0001" / "qc.json"

        # minimal preview artefact
        preview_path.write_bytes(b"\x00")

        # 1) minimal CineV3 DURUM
        data = {
            "project": {"id": "DEMO"},
            "shots": {
                "SH001": {
                    "id": "SH001",
                    "phase": "FAZ_1",
                    "status": "PLANNED",
                    "inputs": {"prompt": "x"},
                    "outputs": {"preview.mp4": "outputs/v0001/preview.mp4"},
                    "history": [],
                }
            },
        }
        durum_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # validate ok
        r = run("validate", str(durum_path))
        if r.returncode != 0:
            return fail("cinev3_validate_minimal", r)
        ok("cinev3_validate_minimal")

        # PLANNED -> IN_PROGRESS -> QC
        r = run("transition", str(durum_path), "SH001", "--to", "IN_PROGRESS")
        if r.returncode != 0:
            return fail("cinev3_to_in_progress", r)
        ok("cinev3_to_in_progress")

        r = run("transition", str(durum_path), "SH001", "--to", "QC")
        if r.returncode != 0:
            return fail("cinev3_to_qc", r)
        ok("cinev3_to_qc")

        # 2) QC->DONE must fail if qc.json missing
        r = run("transition", str(durum_path), "SH001", "--to", "DONE")
        if r.returncode == 0:
            print("❌ cinev3_qc_to_done_requires_qcjson: expected fail but succeeded")
            return 1
        ok("cinev3_qc_to_done_requires_qcjson")

        # 3) add qc.json path but invalid content -> fail
        d = json.loads(durum_path.read_text(encoding="utf-8"))
        d["shots"]["SH001"]["outputs"]["qc.json"] = "outputs/v0001/qc.json"
        durum_path.write_text(json.dumps(d, indent=2), encoding="utf-8")

        qc_path.write_text("[]", encoding="utf-8")  # invalid: not object

        r = run("transition", str(durum_path), "SH001", "--to", "DONE")
        if r.returncode == 0:
            print("❌ cinev3_qc_to_done_requires_qc_object: expected fail but succeeded")
            return 1
        ok("cinev3_qc_to_done_requires_qc_object")

        # 4) valid qc.json -> should pass DONE
        qc_path.write_text(json.dumps({"ok": True, "errors": []}, indent=2), encoding="utf-8")

        r = run("transition", str(durum_path), "SH001", "--to", "DONE")
        if r.returncode != 0:
            return fail("cinev3_qc_to_done_pass", r)
        ok("cinev3_qc_to_done_pass")

        # final validate still ok
        r = run("validate", str(durum_path))
        if r.returncode != 0:
            return fail("cinev3_validate_after_done", r)
        ok("cinev3_validate_after_done")

    print("✅ OK\n\n🎉 TÜM CINEV3 CONTRACT TESTLERİ BAŞARILI")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
