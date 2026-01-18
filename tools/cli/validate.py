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
    repo_root = Path(__file__).resolve().parents[2]

    # load once to detect format
    try:
        durum = _load_json(args.path)
    except Exception as e:
        return _fail(f"Cannot read DURUM file: {e}")

    # CineV2 format
    if "active_project" in durum and "current_focus" in durum and "last_updated_utc" in durum:
        schema_path = repo_root / "schema" / "shot.schema.json"
        return validate_durum(args.path, str(schema_path))

    # CineV3 format
    if "project" in durum and "shots" in durum:
        schema_path = repo_root / "schema" / "cinev3" / "durum.schema.json"
        return validate_durum_v3(args.path, str(schema_path))

    return _fail("Unknown DURUM format (ne CineV2 ne CineV3 top-level alanları bulundu)")

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

def validate_durum_v3(durum_path: str, schema_path: str) -> int:
    # 1) load
    try:
        durum = _load_json(durum_path)
    except Exception as e:
        return _fail(f"Cannot read DURUM file: {e}")

    # 2) load schema
    try:
        schema = _load_json(schema_path)
    except Exception as e:
        return _fail(f"Cannot read schema file: {e}")

    # 3) jsonschema validate whole document
    try:
        from jsonschema import Draft7Validator
    except Exception:
        return _fail("Missing dependency: jsonschema. Install with: python -m pip install jsonschema")

    v = Draft7Validator(schema)
    errors = sorted(v.iter_errors(durum), key=lambda e: list(e.path))

    if errors:
        print("[FAIL] Validation errors:", file=sys.stderr)
        for err in errors:
            path = ".".join(str(p) for p in err.path) if err.path else "<root>"
            print(f"  - {path}: {err.message}", file=sys.stderr)
        return 1

    # 4) enforce shot key == shot.id consistency (same kural CineV2 gibi)
    shots = durum.get("shots")
    if not isinstance(shots, dict):
        return _fail("shots must be an object/dictionary (NOT an array/list)")

    bad = []
    for shot_id, shot in shots.items():
        if not isinstance(shot, dict):
            bad.append(f"{shot_id}: shot value must be object")
            continue
        if shot.get("id") != shot_id:
            bad.append(f"{shot_id}: shot.id must equal the key name")

    if bad:
        print("[FAIL] Validation errors:", file=sys.stderr)
        for e in bad:
            print(f"  - {e}", file=sys.stderr)
        return 1

    # 5) qc.json validation (mevcut CineV2 davranışıyla aynı yaklaşım)
    qc_schema_path = Path(__file__).resolve().parents[2] / "schema" / "qc.schema.json"
    qc_schema = None

    if qc_schema_path.exists():
        try:
            qc_schema = _load_json(str(qc_schema_path))
            from jsonschema import Draft7Validator as _QCValidator
            qc_validator = _QCValidator(qc_schema)
        except Exception as e:
            return _fail(f"Cannot load qc.schema.json: {e}")

    for shot_id, shot in shots.items():
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

    return _ok(f"{durum_path} is valid (cinev3 shots={len(shots)})")

