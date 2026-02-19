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
    "RELEASE": set(),  # terminal
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

    # -------------------------
    # NORMALIZATION
    # -------------------------
    shot_id = str(shot_id).strip()
    to_status = str(to_status).strip().upper()

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

    if not cur:
        return _fail("shot status missing")

    cur = str(cur).strip().upper()
    # no-op transition is not allowed (e.g., IN_PROGRESS -> IN_PROGRESS)
    if cur == to_status:
        return _fail(f"invalid transition: {cur} -> {to_status}")

    if cur in IMMUTABLE_STATUSES:
        return _fail(f"immutable status: {cur}")

    allowed = AUTHORITATIVE_TRANSITIONS.get(cur)
    if not allowed or to_status not in allowed:
        return _fail(f"invalid transition: {cur} -> {to_status}")

    # -------------------------
    # IN_PROGRESS -> QC gate
    # -------------------------
    if cur == "IN_PROGRESS" and to_status == "QC":
        outputs = shot.get("outputs") or {}
        if not isinstance(outputs, dict) or len(outputs) == 0:
            return _fail("IN_PROGRESS -> QC requires non-empty outputs")

    # -------------------------
    # QC -> DONE hard gate
    # -------------------------
    if cur == "QC" and to_status == "DONE":
        outputs = shot.get("outputs") or {}
        qc_rel = outputs.get("qc.json")
        prev_rel = outputs.get("preview.mp4")

        # key yoksa
        if not qc_rel or not prev_rel:
            return _fail("QC -> DONE requires qc.json and preview.mp4 file to exist on disk")

        for rel in [qc_rel, prev_rel]:
            rel_path = Path(rel)

            if rel_path.is_absolute():
                return _fail("absolute paths are not allowed in outputs")

            if ".." in rel_path.parts:
                return _fail("path traversal detected in outputs")

            if not str(rel).startswith("outputs/"):
                return _fail("outputs must be inside outputs/ directory")

            full = (p.parent / rel_path).resolve()

            # dosya disk'te yoksa da AYNI mesaj dön
            if not full.exists():
                return _fail("QC -> DONE requires qc.json and preview.mp4 file to exist on disk")
            # qc.json ok==true şartı (S5 için)
            try:
                qc_abs = (p.parent / Path(qc_rel)).resolve()
                qc_data = json.loads(qc_abs.read_text(encoding="utf-8"))
            except Exception:
                return _fail("QC -> DONE requires qc.json ok==true")

            if qc_data.get("ok") is not True:
                return _fail("QC -> DONE requires qc.json ok==true")

    # -------------------------
    # DONE -> RELEASE gate
    # -------------------------
    if cur == "DONE" and to_status == "RELEASE":
        outputs = shot.get("outputs") or {}
        if not outputs:
            return _fail("DONE -> RELEASE requires outputs")

    # APPLY TRANSITION (genel)
    shot["status"] = to_status
    shots[shot_id] = shot
    durum["shots"] = shots

    try:
        p.write_text(
            json.dumps(durum, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except Exception as e:
        return _fail(f"failed to write DURUM.json: {e}")

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






