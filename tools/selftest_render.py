import json
import shutil
import subprocess
import sys
from pathlib import Path


def _fail(msg: str, code: int = 1) -> int:
    print(f"❌ FAIL: {msg}")
    return code


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    # stdout/stderr'ı yakala ki CI'de hata ayıklamak kolay olsun
    return subprocess.run(cmd, text=True, capture_output=True)


def _reset_dir(p: Path) -> None:
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True, exist_ok=True)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]

    # Selftest'in tüm çalışma alanı repo içinde olmalı (render artık bunu istiyor)
    tmp_root = repo_root / "outputs" / ".tmp" / "selftest_render"
    src_dir = tmp_root / "src"
    out_dir = tmp_root / "out"
    _reset_dir(tmp_root)
    _reset_dir(src_dir)
    _reset_dir(out_dir)

    src_preview = repo_root / "outputs" / "v0001" / "preview.mp4"
    if not src_preview.exists():
        return _fail(f"missing source preview: {src_preview}")

    src_durum = repo_root / "DURUM.json"
    if not src_durum.exists():
        return _fail(f"missing DURUM.json: {src_durum}")

    # Repo'daki DURUM.json'u değiştirmemek için repo içi temp kopya üzerinde çalış
    tmp_durum = tmp_root / "DURUM.json"
    shutil.copyfile(src_durum, tmp_durum)

    # Kaynak preview'i de repo içi temp'e kopyala (tam izole olsun)
    tmp_preview = src_dir / "preview.mp4"
    shutil.copyfile(src_preview, tmp_preview)

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
        str(tmp_preview),
    ]

    p = _run(cmd)
    if p.returncode != 0:
        print("---- stdout ----")
        print(p.stdout)
        print("---- stderr ----")
        print(p.stderr)
        return _fail(f"render exited non-zero: {p.returncode}", code=2)

    # 1) out/preview.mp4 var mı
    preview_out = out_dir / "preview.mp4"
    if not preview_out.exists():
        return _fail(f"preview not created: {preview_out}")

    # 2) temp DURUM.json içinde shots[SH008].outputs['preview.mp4'] yazıldı mı
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

    # Relatif yazıldıysa repo_root'a göre tamamla (render'in sözleşmesi bu olmalı)
    if not got_path.is_absolute():
        got_path = (repo_root / got_path)

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

