
import json
from datetime import datetime, timezone

ALLOWED = {
    "PLANNED": {"IN_PROGRESS"},
    "IN_PROGRESS": {"BLOCKED", "DONE"},
    "BLOCKED": {"IN_PROGRESS"},
    "DONE": set(),
}

def _utc_z_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def cmd_transition(args) -> int:
    path = args.path
    shot_id = args.shot_id
    to_status = args.to

    try:
        with open(path, "r", encoding="utf-8") as f:
            durum = json.load(f)
    except Exception as e:
        print(f"[ERR] cannot read {path}: {e}")
        return 2

    shots = durum.get("shots", {})
    if shot_id not in shots:
        print(f"[ERR] shot not found: {shot_id}")
        return 2

    shot = shots[shot_id]
    cur = shot.get("status")
    if cur not in ALLOWED:
        print(f"[ERR] invalid current status: {cur}")
        return 2

    if to_status not in ALLOWED[cur]:
        print(f"[ERR] illegal transition: {cur} -> {to_status}")
        return 2

    now = _utc_z_now()
    shot["status"] = to_status
    shot.setdefault("history", []).append({
        "event": "STATUS_CHANGED",
        "from": cur,
        "to": to_status,
        "at": now,
        "by": "cli",
    })
    durum["last_updated_utc"] = now

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(durum, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except Exception as e:
        print(f"[ERR] cannot write {path}: {e}")
        return 2

    print(f"[OK] {shot_id}: {cur} -> {to_status}")
    return 0
