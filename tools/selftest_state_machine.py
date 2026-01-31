import json
import tempfile
from pathlib import Path
import subprocess
import sys

def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "tools.cli", *args],
        text=True,
        capture_output=True,
    )

def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "DURUM.json"

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
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")

        ok_steps = [
            ("transition", str(p), "SH001", "--to", "IN_PROGRESS"),
            ("transition", str(p), "SH001", "--to", "QC"),
        ]

        tested_inprog_idempotency = False

        for step in ok_steps:
            r = run(*step)
            if r.returncode != 0:
                print("❌ expected OK but failed:", step)
                print(r.stdout)
                print(r.stderr)
                return 1

            # Sadece ilk IN_PROGRESS'tan hemen sonra: IN_PROGRESS -> IN_PROGRESS geçersiz olmalı
            if (not tested_inprog_idempotency) and step[-1] == "IN_PROGRESS":
                r2 = run("transition", str(p), "SH001", "--to", "IN_PROGRESS")
                if r2.returncode == 0:
                    print("❌ expected failure: IN_PROGRESS -> IN_PROGRESS, but succeeded")
                    return 1

                combined = (r2.stdout or "") + (r2.stderr or "")
                if "invalid transition" not in combined:
                    print("❌ expected 'invalid transition' message, got:")
                    print("STDOUT:", r2.stdout)
                    print("STDERR:", r2.stderr)
                    return 1

                print("✅ OK (beklenen hata)")
                tested_inprog_idempotency = True

        print("✅ OK")
        print("\n🎉 TÜM STATE MACHINE TESTLERİ BAŞARILI")
        return 0

if __name__ == "__main__":
    raise SystemExit(main())

