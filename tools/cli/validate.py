# tools/cli/validate.py
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone


def _fail(msg: str) -> int:
    print(f"[FAIL] {msg}", file=sys.stderr)
    return 1


def _ok(msg: str) -> int:
    print(f"[OK] {msg}")
    return 0


def _load_json(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _is_iso_utc_z(s: str) -> bool:
    # Accepts "2025-12-30T00:00:00Z"
    try:
        if not s.endswith("Z"):
            return False
        datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
        return True
    except Exception:
        return False
    
from pathlib import Path

def cmd_validate(args) -> int:
    # repo root = .../CINEV2
    repo_root = Path(__file__).resolve().parents[2]
    schema_path = repo_root / "schema" / "shot.schema.json"
    return validate_durum(args.path, str(schema_path))

def validate_durum(durum_path: str, schema_path: str) -> int:
    # 1) basic load
    try:
        durum = _load_json(durum_path)
    except Exception as e:
        return _fail(f"Cannot read DURUM file: {e}")

    # 2) basic structure checks (no dependency)
    required_top = ["active_project", "current_focus", "shots", "last_updated_utc"]
    for k in required_top:
        if k not in durum:
            return _fail(f"Missing top-level key: {k}")

    if not isinstance(durum["shots"], dict):
        return _fail("shots must be an object/dictionary (NOT an array/list)")

    if not _is_iso_utc_z(durum["last_updated_utc"]):
        return _fail("last_updated_utc must be ISO-8601 UTC with Z, e.g. 2025-12-30T00:00:00Z")

    # 3) load shot schema
    try:
        shot_schema = _load_json(schema_path)
    except Exception as e:
        return _fail(f"Cannot read schema file: {e}")

    # 4) jsonschema validate (hard requirement)
    try:
        from jsonschema import Draft7Validator
    except Exception:
        return _fail("Missing dependency: jsonschema. Install with: python -m pip install jsonschema")

    v = Draft7Validator(shot_schema)

    errors = []
    for shot_id, shot in durum["shots"].items():
        if not isinstance(shot, dict):
            errors.append(f"{shot_id}: shot value must be object")
            continue

        # enforce key==id consistency
        if shot.get("id") != shot_id:
            errors.append(f"{shot_id}: shot.id must equal the key name")

        for err in sorted(v.iter_errors(shot), key=lambda e: list(e.path)):
            path = ".".join(str(p) for p in err.path) if err.path else "<root>"
            errors.append(f"{shot_id}:{path}: {err.message}")

    if errors:
        print("[FAIL] Validation errors:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    
    # --- QC report validation (hardening) ---
    qc_schema_path = Path(__file__).resolve().parents[2] / "schema" / "qc.schema.json"
    qc_schema = None

    if qc_schema_path.exists():
        try:
            qc_schema = _load_json(str(qc_schema_path))
            from jsonschema import Draft7Validator as _QCValidator
            qc_validator = _QCValidator(qc_schema)
        except Exception as e:
            return _fail(f"Cannot load qc.schema.json: {e}")

    for shot_id, shot in durum["shots"].items():
        outputs = shot.get("outputs") or {}
        if not isinstance(outputs, dict):
            continue

        if "qc.json" not in outputs:
            continue

        qc_rel = outputs["qc.json"]
        qc_path = (Path(durum_path).parent / qc_rel).resolve()

        if not qc_path.exists():
            return _fail(f"{shot_id}: qc.json declared but file missing: {qc_rel}")

        if qc_schema:
            try:
                qc_data = _load_json(str(qc_path))
            except Exception as e:
                return _fail(f"{shot_id}: qc.json unreadable: {e}")

            qc_errors = sorted(qc_validator.iter_errors(qc_data), key=lambda e: e.path)
            if qc_errors:
                msg = "; ".join([f"{'/'.join(map(str, e.path))}: {e.message}" for e in qc_errors])
                return _fail(f"{shot_id}: qc.json schema invalid: {msg}")

    return _ok(f"{durum_path} is valid (shots={len(durum['shots'])})")
