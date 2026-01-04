import json
from pathlib import Path
from datetime import datetime, timezone

def _fail(msg: str) -> int:
    print(f"[FAIL] {msg}")
    return 1

def _ok(msg: str) -> int:
    print(f"[OK] {msg}")
    return 0

def _load_json(p: str) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))

def cmd_qc(args) -> int:
    durum_path = args.durum
    shot_id = args.shot_id
    out_dir = Path(args.out)

    durum = _load_json(durum_path)
    shots = durum.get("shots", {})
    shot = shots.get(shot_id)

    if not isinstance(shot, dict):
        return _fail(f"{shot_id}: shot not found in DURUM")

    out_dir.mkdir(parents=True, exist_ok=True)

    qc_path = out_dir / "qc.json"
    # --- REAL QC CHECK (minimum) ---
    errors = []
    preview_path = out_dir / "preview.mp4"

    if not preview_path.exists():
        errors.append("missing preview.mp4")

    qc = {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": [],
        "note": "qc pass" if not errors else "qc failed",
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    qc_path.write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")

    # DURUM outputs'a yaz (qc.json key'in proje standardınla aynı olmalı)
    outputs = shot.get("outputs")
    if not isinstance(outputs, dict):
        shot["outputs"] = {}
        outputs = shot["outputs"]
    outputs["qc.json"] = str(qc_path.as_posix())

    # last_updated_utc güncelle
    durum["last_updated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    Path(durum_path).write_text(json.dumps(durum, ensure_ascii=False, indent=2), encoding="utf-8")

    return _ok(f"{shot_id}: wrote {qc_path}")
