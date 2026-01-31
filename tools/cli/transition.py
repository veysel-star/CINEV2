import argparse
import json
import os
import sys
from pathlib import Path


IMMUTABLE_STATUSES = {"RELEASE"}

AUTHORITATIVE_TRANSITIONS = {
    "PLANNED": {"IN_PROGRESS"},
    "IN_PROGRESS": {"QC"},
    "QC": {"DONE"},
    "DONE": {"RELEASE"},
}


def _fail(msg: str) -> int:
    print("[ERR]", msg)
    return 2


def cmd_transition(args) -> int:
    path = getattr(args, "durum", None) or getattr(args, "path", None) or getattr(args, "durum_json", None)
    shot_id = getattr(args, "shot_id", None) or getattr(args, "shot", None) or getattr(args, "id", None)
    to_status = getattr(args, "to", None) or getattr(args, "to_status", None) or getattr(args, "status", None)

    if not path:
        return _fail("missing DURUM.json path argument")
    if not shot_id:
        return _fail("missing shot_id argument")
    if not to_status:
        return _fail("missing --to target status")

    p = Path(path)
    if not p.exists():
        return _fail(f"missing DURUM.json: {path}")

    try:
        durum = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return _fail(f"DURUM.json invalid JSON: {e}")

    shots = (durum or {}).get("shots") or {}
    if shot_id not in shots:
        return _fail(f"unknown shot: {shot_id}")

    shot = shots[shot_id]
    cur = shot.get("status")

    if cur in IMMUTABLE_STATUSES:
        return _fail(f"immutable status: {cur}")

    allowed = AUTHORITATIVE_TRANSITIONS.get(cur)
    if not allowed or to_status not in allowed:
        return _fail(f"invalid transition: {cur} -> {to_status}")

    # -------------------------
    # IN_PROGRESS -> QC hard gate
    # -------------------------
    if cur == "IN_PROGRESS" and to_status == "QC":
        outputs = shot.get("outputs") or {}
        if not isinstance(outputs, dict) or len(outputs) == 0:
            return _fail("IN_PROGRESS -> QC requires non-empty outputs")

    # -------------------------
    # QC -> DONE hard gate (FAZ-aware)
    # -------------------------
    if cur == "QC" and to_status == "DONE":
        outputs = shot.get("outputs") or {}
        if not isinstance(outputs, dict) or "qc.json" not in outputs:
            return _fail("QC -> DONE requires outputs['qc.json']")

        qc_rel = outputs.get("qc.json")
        if not isinstance(qc_rel, str) or not qc_rel.strip():
            return _fail("QC -> DONE requires outputs['qc.json'] to be a non-empty string path")

        durum_dir = Path(path).resolve().parent
        qc_path = (durum_dir / qc_rel).resolve()

        if not qc_path.exists() or not qc_path.is_file():
            return _fail("QC -> DONE requires qc.json file to exist on disk")

        # read qc.json once
        try:
            qc_data = json.loads(qc_path.read_text(encoding="utf-8"))
        except Exception as e:
            return _fail(f"QC -> DONE requires qc.json to be valid JSON: {e}")

        if not isinstance(qc_data, dict):
            return _fail("QC -> DONE requires qc.json to be a JSON object")

        # optional schema validation if schema/qc.schema.json exists
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
                parts = []
                for e in qc_errors[:8]:
                    path_s = "/".join(map(str, e.path)) if e.path else "<root>"
                    parts.append(f"{path_s}: {e.message}")
                return _fail("QC -> DONE requires qc.json to match qc.schema.json: " + "; ".join(parts))

        # qc pass must be explicit
        if qc_data.get("ok") is not True:
            return _fail("QC -> DONE requires qc.json ok==true")
        if qc_data.get("errors") not in (None, [], ()):
            return _fail("QC -> DONE requires qc.json errors==[]")

        # FAZ_2 hard rule
        if shot.get("phase") == "FAZ_2":
            metrics = qc_data.get("metrics") or {}
            if not isinstance(metrics, dict):
                return _fail("FAZ_2 requires qc.json metrics to be an object")
            if metrics.get("character_passive_status") != "PASSIVE_OK":
                return _fail("FAZ_2 requires character_passive_status == PASSIVE_OK")

        # also require preview.mp4 exists
        if "preview.mp4" not in outputs:
            return _fail("QC -> DONE requires outputs['preview.mp4']")
        prev_rel = outputs.get("preview.mp4")
        if not isinstance(prev_rel, str) or not prev_rel.strip():
            return _fail("QC -> DONE requires outputs['preview.mp4'] to be a non-empty string path")
        prev_path = (durum_dir / prev_rel).resolve()
        if not prev_path.exists() or not prev_path.is_file():
            return _fail("QC -> DONE requires preview.mp4 file to exist on disk")

    # -------------------------
    # DONE -> RELEASE: run release gate
    # -------------------------
    if cur == "DONE" and to_status == "RELEASE":
        project = durum.get("active_project")
        if not isinstance(project, str) or not project.strip():
            return _fail("DONE -> RELEASE requires DURUM.json to have active_project")

        target_release = shot.get("release") or durum.get("active_release") or ""
        if not isinstance(target_release, str) or not target_release.strip():
            return _fail("DONE -> RELEASE requires a release id on shot.release or DURUM.active_release")

        from .release_gate import main as release_gate

        # release_gate exits on fail; successful run returns/prints OK.
        release_gate(["--project", project, "--release", target_release])

    # apply transition
    shot["status"] = to_status
    shots[shot_id] = shot
    durum["shots"] = shots

    try:
        p.write_text(json.dumps(durum, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        return _fail(f"cannot write DURUM.json: {e}")

    print(f"[OK] {shot_id}: {cur} -> {to_status}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="tools.cli transition", add_help=True)
    ap.add_argument("durum", help="Path to DURUM.json")
    ap.add_argument("shot_id", help="Shot id (e.g. SH001)")
    ap.add_argument("--to", required=True, help="Target status (IN_PROGRESS/QC/DONE/RELEASE)")
    args = ap.parse_args(argv)
    return cmd_transition(args)


if __name__ == "__main__":
    raise SystemExit(main())






