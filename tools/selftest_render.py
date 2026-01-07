import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _fail(msg: str, code: int = 1) -> int:
    print(f"❌ FAIL: {msg}")
    return code


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    # stdout/stderr'ı yakala ki CI'de hata ayıklamak kolay olsun
    return subprocess.run(cmd, text=True, capture_output=True)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]

    src_preview = repo_root / "outputs" / "v0001" / "preview.mp4"
    if not src_preview.exists():
        return _fail(f"missing source preview: {src_preview}")

    src_durum = repo_root / "DURUM.json"
    if not src_durum.exists():
        return _fail(f"missing DURUM.json: {src_durum}")

    # ÖNEMLİ: Repo'daki DURUM.json'u değiştirmemek için temp kopya üzerinde çalışıyoruz.
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        tmp_durum = td_path / "DURUM.json"
        shutil.copyfile(src_durum, tmp_durum)

        out_dir = td_path / "outputs_vTEST"
        out_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable,
            "-m",
            "tools.cli",
            "render",
            str(tmp_durum),
            "SH008",
            "--out",
            str(out_dir),
            "--src",
            str(src_preview),
        ]

        p = _run(cmd)
        if p.returncode != 0:
            print("---- stdout ----")
            print(p.stdout)
            print("---- stderr ----")
            print(p.stderr)
            return _fail(f"render exited non-zero: {p.returncode}")

        # 1) outputs/<out>/preview.mp4 var mı
        preview_out = out_dir / "preview.mp4"
        if not preview_out.exists():
            return _fail(f"preview not created: {preview_out}")

        # 2) DURUM.json içinde shots[SH008].outputs['preview.mp4'] yazıldı mı
        try:
            d = json.loads(tmp_durum.read_text(encoding="utf-8"))
        except Exception as e:
            return _fail(f"cannot read temp DURUM.json: {e}")

        shots = d.get("shots", {})
        if "SH008" not in shots:
            return _fail("SH008 not found in temp DURUM.json")

        outputs = (shots["SH008"] or {}).get("outputs", {}) or {}
        got = outputs.get("preview.mp4")
        if not got:
            return _fail("shots['SH008'].outputs['preview.mp4'] missing")

        # path karşılaştırması (normalize)
        expected = preview_out.resolve().as_posix()
        got_norm = str(got).replace("\\", "/")
        got_path = Path(got_norm)

        # Relatif yazıldıysa temp çalışma dizinine göre tamamla
        if not got_path.is_absolute():
            got_path = (td_path / got_path)

        got_resolved = got_path.resolve().as_posix()

        if got_resolved != expected:
            return _fail(
                "outputs['preview.mp4'] mismatch\n"
                f"expected: {expected}\n"
                f"     got: {got_norm}\n"
                f"resolved: {got_resolved}"
            )

    print("✅ OK")
    print("\n🎉 TÜM RENDER TESTLERİ BAŞARILI")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
