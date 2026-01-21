import json
from datetime import datetime, timezone
from pathlib import Path

# Authoritative rules MUST match docs/CINEV2_PIPELINE_RULES.md
# Strict production flow: PLANNED -> IN_PROGRESS -> DONE
# Strict production flow: PLANNED -> IN_PROGRESS -> QC -> DONE
AUTHORITATIVE_TRANSITIONS = {
    "PLANNED": {"IN_PROGRESS"},
    "IN_PROGRESS": {"QC", "BLOCKED", "FAIL"},
    "QC": {"DONE", "RETRY", "BLOCKED", "FAIL"}, 
    "RETRY": {"IN_PROGRESS", "FAIL"},
    "BLOCKED": {"IN_PROGRESS", "FAIL"},
    "DONE": ("RELEASE"),  # terminal
    "RELEASE": set(), 
    "FAIL": set(),  # terminal
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

    # RELEASE is final / immutable
    if cur == "RELEASE":  
        return _fail(f"immutable status: {cur}")

    # Hard enforcement: only statuses in AUTHORITATIVE_TRANSITIONS are supported.
    # If a shot is BLOCKED (or anything else), it is outside authoritative rules.
    if cur not in AUTHORITATIVE_TRANSITIONS:
        return _fail(f"unsupported current status by authoritative rules: {cur}")

    allowed_next = AUTHORITATIVE_TRANSITIONS[cur]
    if to_status not in allowed_next:
        # exact message format requested
        return _fail(f"invalid transition: {cur} -> {to_status}")
    
    # CineV4: DONE -> RELEASE hard gate
    if cur == "DONE" and to_status == "RELEASE":
        target_release = getattr(args, "release", None)
        if not target_release:
            return _fail("DONE -> RELEASE requires --release <release_id>")

        from .release_gate import main as release_gate
        release_gate([
            "--project", durum.get("active_project"),
            "--release", target_release
        ])

    
    # IN_PROGRESS -> QC hard gate
    if cur == "IN_PROGRESS" and to_status == "QC":
        outputs = shot.get("outputs") or {}
        if not isinstance(outputs, dict) or len(outputs) == 0:
            return _fail("IN_PROGRESS -> QC requires non-empty outputs")
   
    # QC -> DONE: qc.json must exist on disk (hard gate)
    if cur == "QC" and to_status == "DONE":
        outputs = shot.get("outputs") or {}
        if not isinstance(outputs, dict) or "qc.json" not in outputs:
            return _fail("QC -> DONE requires outputs['qc.json']")

        qc_rel = outputs["qc.json"]
        if not isinstance(qc_rel, str) or not qc_rel.strip():
            return _fail("QC -> DONE requires outputs['qc.json'] to be a non-empty string path")

        durum_dir = Path(path).resolve().parent
        qc_path = (durum_dir / qc_rel).resolve()

        if not qc_path.exists() or not qc_path.is_file():
            return _fail("QC -> DONE requires qc.json file to exist on disk")

        # QC -> DONE: qc.json content must indicate pass (hard gate)
        try:
            qc_data = json.loads(qc_path.read_text(encoding="utf-8"))
        except Exception as e:
            return _fail(f"QC -> DONE requires qc.json to be valid JSON: {e}")

        if not isinstance(qc_data, dict):
            return _fail("QC -> DONE requires qc.json to be a JSON object")
        
                # QC -> DONE: qc.json must match schema/qc.schema.json if schema exists
        qc_schema_path = (Path(__file__).resolve().parents[2] / "schema" / "qc.schema.json")
        if qc_schema_path.exists():
            try:
                from jsonschema import Draft7Validator
            except Exception:
                return _fail("QC -> DONE requires jsonschema dependency (pip install jsonschema)")

            try:
                qc_schema = json.loads(qc_schema_path.read_text(encoding="utf-8"))
            except Exception as e:
                return _fail(f"QC -> DONE cannot read qc.schema.json: {e}")

            v = Draft7Validator(qc_schema)
            qc_errors = sorted(v.iter_errors(qc_data), key=lambda e: list(e.path))
            if qc_errors:
                # kısa hata mesajı: ilk birkaç hata yeter
                parts = []
                for e in qc_errors[:8]:
                    path = "/".join(map(str, e.path)) if e.path else "<root>"
                    parts.append(f"{path}: {e.message}")
                return _fail("QC -> DONE requires qc.json to match qc.schema.json: " + "; ".join(parts))

        ok = qc_data.get("ok", None)
        errors = qc_data.get("errors", None)

        if ok is not True:
            return _fail("QC -> DONE requires qc.json ok:true")

        if not isinstance(errors, list):
            return _fail("QC -> DONE requires qc.json errors:[]")

        if len(errors) != 0:
            return _fail("QC -> DONE requires qc.json errors to be empty")
        
        # QC -> DONE also requires preview.mp4
        if "preview.mp4" not in outputs:
            return _fail("QC -> DONE requires outputs['preview.mp4']")

        prev_rel = outputs["preview.mp4"]
        if not isinstance(prev_rel, str) or not prev_rel.strip():
            return _fail("QC -> DONE requires outputs['preview.mp4'] to be a non-empty string path")

        prev_path = (durum_dir / prev_rel).resolve()
        if not prev_path.exists() or not prev_path.is_file():
            return _fail("QC -> DONE requires preview.mp4 file to exist on disk")

    # Gate rules (hard)
    if cur == "IN_PROGRESS" and to_status == "QC":
        outputs = shot.get("outputs") or {}
        if not isinstance(outputs, dict) or len(outputs) == 0:
            return _fail("IN_PROGRESS -> QC requires non-empty outputs")

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


