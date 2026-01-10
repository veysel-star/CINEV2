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

        # Minimal DURUM with 1 shot
        data = {
            "project": {"id": "DEMO"},
            "shots": {
                "SH001": {
                    "id": "SH001",
                    "phase": "FAZ_1",
                    "status": "PLANNED",
                    "inputs": {"prompt": "x"},
                    "outputs": { "preview.mp4": "outputs/v0001/preview.mp4"},
                    "history": [],
                }
            },
        }
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # Allowed transitions (should succeed)
        ok_steps = [
            ("transition", str(p), "SH001", "--to", "IN_PROGRESS"),
            ("transition", str(p), "SH001", "--to", "BLOCKED"),
            ("transition", str(p), "SH001", "--to", "IN_PROGRESS"),
            ("transition", str(p), "SH001", "--to", "QC"),
            ("transition", str(p), "SH001", "--to", "RETRY"),
            ("transition", str(p), "SH001", "--to", "IN_PROGRESS"),
            ("transition", str(p), "SH001", "--to", "FAIL"),
        ]
        for step in ok_steps:
            r = run(*step)
            if r.returncode != 0:
                print("❌ expected OK but failed:", step)
                print(r.stdout)
                print(r.stderr)
                return 1

        # Now FAIL is terminal -> any move should fail
        r = run("transition", str(p), "SH001", "--to", "IN_PROGRESS")
        if r.returncode == 0:
            print("❌ expected failure from FAIL -> IN_PROGRESS, but succeeded")
            return 1

        print("✅ OK")
        print("\n🎉 TÜM STATE MACHINE TESTLERİ BAŞARILI")
        return 0

if __name__ == "__main__":
    raise SystemExit(main())
