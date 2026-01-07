import json
from datetime import datetime, timezone
from pathlib import Path

def _fail(msg: str) -> int:
    print(f"[ERR] {msg}")
    return 2

def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

def cmd_newshot(args) -> int:
    path = Path(args.path)

    if not path.exists() or not path.is_file():
        return _fail(f"cannot read {path}")

    try:
        durum = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return _fail(f"invalid json: {e}")

    shots = durum.get("shots")
    if not isinstance(shots, dict):
        return _fail("DURUM.json: 'shots' must be an object")

    shot_id = args.shot_id
    if shot_id in shots:
        return _fail(f"shot already exists: {shot_id}")

    now = _utc_now()

    shots[shot_id] = {
        "id": shot_id,
        "phase": "FAZ_1",
        "status": "PLANNED",
        "inputs": {
            "prompt": args.prompt
        },
        "outputs": {},
        "history": [
            {
                "event": "CREATED",
                "at": now,
                "by": "system"
            },
            {
                "event": "PLANNING_DECISION",
                "at": now,
                "by": "user",
                "note": "initial shot planning completed"
            }
        ]
    }

    durum["shots"] = shots
    durum["last_updated_utc"] = now

    path.write_text(
        json.dumps(durum, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"[OK] created shot {shot_id}")
    return 0
