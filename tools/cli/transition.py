import json
from datetime import datetime, timezone


# Authoritative rules MUST match docs/CINEV2_PIPELINE_RULES.md
# Strict production flow: PLANNED -> IN_PROGRESS -> DONE
AUTHORITATIVE_TRANSITIONS = {
    "PLANNED": {"IN_PROGRESS"},
    "IN_PROGRESS": {"DONE"},
    "DONE": set(),
}


def _utc_z_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _fail(msg: str) -> int:
    print(f"[ERR] {msg}")
    return 2


def cmd_transition(args) -> int:
    path = args.path
    shot_id = args.shot_id
    to_status = args.to

    try:
        with open(path, "r", encoding="utf-8") as f:
            durum = json.load(f)
    except Exception as e:
        return _fail(f"cannot read {path}: {e}")

    shots = durum.get("shots", {})
    if shot_id not in shots:
        return _fail(f"shot not found: {shot_id}")

    shot = shots[shot_id]
    cur = shot.get("status")

    # Hard enforcement: only statuses in AUTHORITATIVE_TRANSITIONS are supported.
    # If a shot is BLOCKED (or anything else), it is outside authoritative rules.
    if cur not in AUTHORITATIVE_TRANSITIONS:
        return _fail(f"unsupported current status by authoritative rules: {cur}")

    allowed_next = AUTHORITATIVE_TRANSITIONS[cur]
    if to_status not in allowed_next:
        # exact message format requested
        return _fail(f"invalid transition: {cur} -> {to_status}")

    now = _utc_z_now()

    # Apply transition
    shot["status"] = to_status
    shot.setdefault("history", []).append(
        {
            "event": "STATUS_CHANGED",
            "from": cur,
            "to": to_status,
            "at": now,
            "by": "cli",
        }
    )
    durum["last_updated_utc"] = now

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(durum, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except Exception as e:
        return _fail(f"cannot write {path}: {e}")

    print(f"[OK] {shot_id}: {cur} -> {to_status}")
    return 0


