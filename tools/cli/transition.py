import json
from datetime import datetime, timezone
from pathlib import Path

# Minimum sizes to reject fake artifacts
MP4_MIN_BYTES = 1024
QC_JSON_MIN_BYTES = 20


def _file_min_bytes(path: Path, n: int) -> bool:
    try:
        return path.is_file() and path.stat().st_size >= n
    except Exception:
        return False


def _looks_like_mp4(path: Path) -> bool:
    # minimal MP4 sanity: ftyp box usually appears near beginning
    try:
        with path.open("rb") as f:
            head = f.read(4096)
        return b"ftyp" in head
    except Exception:
        return False


def _is_valid_json_file(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
        json.loads(text)
        return True
    except Exception:
        return False


# Authoritative rules MUST match docs/CINEV2_PIPELINE_RULES.md
AUTHORITATIVE_TRANSITIONS = {
    "PLANNED": {"IN_PROGRESS"},
    "IN_PROGRESS": {"QC", "BLOCKED"},
    "QC": {"DONE", "IN_PROGRESS"},  # revisions allowed
    "BLOCKED": {"IN_PROGRESS"},
    "DONE": set(),  # terminal
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
    if cur not in AUTHORITATIVE_TRANSITIONS:
        return _fail(f"unsupported current status by authoritative rules: {cur}")

    allowed_next = AUTHORITATIVE_TRANSITIONS[cur]
    if to_status not in allowed_next:
        return _fail(f"invalid transition: {cur} -> {to_status}")

    durum_dir = Path(path).resolve().parent

    # Gate rules (hard): IN_PROGRESS -> QC requires minimum artifacts and disk validation
    if cur == "IN_PROGRESS" and to_status == "QC":
        outputs = shot.get("outputs") or {}
        if not isinstance(outputs, dict) or len(outputs) == 0:
            return _fail("IN_PROGRESS -> QC requires non-empty outputs")

        # required evidence artifacts
        if "preview.mp4" not in outputs:
            return _fail("IN_PROGRESS -> QC requires outputs['preview.mp4']")
        if "qc.json" not in outputs:
            return _fail("IN_PROGRESS -> QC requires outputs['qc.json']")

        # validate output paths are non-empty strings
        for k in ("preview.mp4", "qc.json"):
            v = outputs.get(k)
            if not isinstance(v, str) or not v.strip():
                return _fail(f"IN_PROGRESS -> QC requires outputs['{k}'] to be a non-empty string path")

        preview_path = (durum_dir / outputs["preview.mp4"]).resolve()
        qc_path = (durum_dir / outputs["qc.json"]).resolve()

        # must exist on disk
        if not preview_path.exists() or not preview_path.is_file():
            return _fail("IN_PROGRESS -> QC requires preview.mp4 file to exist on disk")
        if not qc_path.exists() or not qc_path.is_file():
            return _fail("IN_PROGRESS -> QC requires qc.json file to exist on disk")

        # must not be tiny / fake
        if not _file_min_bytes(preview_path, MP4_MIN_BYTES):
            return _fail(f"IN_PROGRESS -> QC requires preview.mp4 to be at least {MP4_MIN_BYTES} bytes")
        if not _file_min_bytes(qc_path, QC_JSON_MIN_BYTES):
            return _fail(f"IN_PROGRESS -> QC requires qc.json to be at least {QC_JSON_MIN_BYTES} bytes")

        # format sanity
        if not _looks_like_mp4(preview_path):
            return _fail("IN_PROGRESS -> QC requires preview.mp4 to look like a real MP4 (ftyp missing)")
        if not _is_valid_json_file(qc_path):
            return _fail("IN_PROGRESS -> QC requires qc.json to be valid JSON")

    # QC -> DONE: qc.json must exist on disk AND be valid (hard gate)
    if cur == "QC" and to_status == "DONE":
        outputs = shot.get("outputs") or {}
        if not isinstance(outputs, dict) or "qc.json" not in outputs:
            return _fail("QC -> DONE requires outputs['qc.json']")

        qc_rel = outputs["qc.json"]
        if not isinstance(qc_rel, str) or not qc_rel.strip():
            return _fail("QC -> DONE requires outputs['qc.json'] to be a non-empty string path")

        qc_path = (durum_dir / qc_rel).resolve()

        if not qc_path.exists() or not qc_path.is_file():
            return _fail("QC -> DONE requires qc.json file to exist on disk")

        if not _file_min_bytes(qc_path, QC_JSON_MIN_BYTES):
            return _fail(f"QC -> DONE requires qc.json to be at least {QC_JSON_MIN_BYTES} bytes")

        if not _is_valid_json_file(qc_path):
            return _fail("QC -> DONE requires qc.json to be valid JSON")

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



