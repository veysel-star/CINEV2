import json
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime, timezone

import cv2
from jsonschema import validate, ValidationError


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _utc_iso_from_mtime(p: Path) -> str:
    ts = p.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fail(msg: str) -> int:
    print(f"[FAIL] {msg}")
    return 1


def _ok(msg: str) -> int:
    print(f"[OK] {msg}")
    return 0


def _load_json(p: str) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _find_faz2_char_id(shot: dict) -> str | None:
    """Find last FAZ2_LOCKS event and extract character_lock.id from its note JSON."""
    hist = shot.get("history", [])
    if not isinstance(hist, list):
        return None

    last = None
    for e in hist:
        if isinstance(e, dict) and e.get("event") == "FAZ2_LOCKS":
            last = e

    if not last:
        return None

    note = last.get("note", "")
    if not isinstance(note, str) or not note.strip():
        return None

    try:
        data = json.loads(note)
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    cl = data.get("character_lock", {})
    if not isinstance(cl, dict):
        return None

    cid = cl.get("id")
    return cid if isinstance(cid, str) and cid.strip() else None

def _extract_frames_ffmpeg(preview_path: Path, frames_dir: Path) -> list[Path]:
    """Extract 3 frames within a 1s clip using ffmpeg. Returns list of frame paths created."""
    frames_dir.mkdir(parents=True, exist_ok=True)
    out_paths: list[Path] = []

    # video ~1.00s, so sample within duration
    stamps = [0.2, 0.5, 0.8]
    for i, t in enumerate(stamps, start=1):
        out_img = frames_dir / f"f{i:02d}.png"
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            str(t),
            "-i",
            str(preview_path),
            "-frames:v",
            "1",
            "-update",
            "1",
            str(out_img),
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        if out_img.exists() and out_img.stat().st_size > 0:
            out_paths.append(out_img)

    return out_paths

def _detect_face_any(frames: list[Path]) -> bool:
    """Detect face in any frame using OpenCV Haar cascade."""
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(str(cascade_path))

    for fp in frames:
        img = cv2.imread(str(fp))
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        if len(faces) > 0:
            return True
    return False


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
    errors: list[str] = []
    warnings: list[str] = []

    # preview path is always under out_dir
    preview_path = out_dir / "preview.mp4"
    preview_exists = preview_path.exists()

    if not preview_exists:
        errors.append("missing preview.mp4")

    # base metrics
    metrics = {
        "preview_exists": preview_exists,
        "preview_bytes": int(preview_path.stat().st_size) if preview_exists else 0,
        "preview_sha256": _sha256_file(preview_path) if preview_exists else "",
        "preview_mtime_utc": _utc_iso_from_mtime(preview_path) if preview_exists else "",
    }

    # -------------------------------
    # FAZ_2 Passive Character Check
    # -------------------------------
    state_root = Path(durum_path).resolve().parent

    char_id = _find_faz2_char_id(shot)
    if not char_id:
        warnings.append("FAZ2_LOCKS missing or invalid; character check not evaluated")

    ref_exists = False
    ref_rel = ""
    if char_id:
        ref_path = state_root / "assets" / "characters" / char_id / "ref.jpg"
        ref_exists = ref_path.exists()
        ref_rel = str(Path("assets") / "characters" / char_id / "ref.jpg")
        if not ref_exists:
            errors.append(f"missing ref.jpg for {char_id} at {ref_rel}")

    frames_extracted = 0
    face_detected = False

    if preview_exists and char_id and ref_exists:
        try:
            frames_dir = out_dir / "_qc_frames"
            frames = _extract_frames_ffmpeg(preview_path, frames_dir)
            frames_extracted = len(frames)
            if frames_extracted == 0:
                errors.append("frame_extract_failed")
            else:
                face_detected = _detect_face_any(frames)
                if not face_detected:
                    errors.append("no_face_detected_in_preview")
        except Exception:
            errors.append("frame_extract_failed")

    # Passive status logic (no identity embedding yet)
    if not char_id:
        passive_status = "NOT_EVALUATED"
    elif not ref_exists:
        passive_status = "FAIL_NO_REF"
    elif not preview_exists:
        passive_status = "FAIL_NO_PREVIEW"
    elif frames_extracted == 0:
        passive_status = "FAIL_NO_FRAMES"
    elif not face_detected:
        passive_status = "FAIL_NO_FACE"
    else:
        passive_status = "PASSIVE_OK"

    # store into metrics (schema may restrict; we'll see on run)
    metrics["char_id"] = char_id or ""
    metrics["ref_path"] = ref_rel
    metrics["ref_exists"] = bool(ref_exists)
    metrics["frames_extracted"] = int(frames_extracted)
    metrics["face_detected"] = bool(face_detected)
    metrics["character_passive_status"] = passive_status

    # artifacts
    artifacts = [
        {"key": "qc.json", "path": str((out_dir / "qc.json").as_posix())}
    ]
    if preview_exists:
        artifacts.append({"key": "preview.mp4", "path": str(preview_path.as_posix())})

    qc = {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "note": "qc pass" if not errors else "qc failed",
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "metrics": metrics,
        "artifacts": artifacts,
    }

    # self-validate qc against schema
    try:
        schema_path = Path(__file__).resolve().parents[2] / "schema" / "qc.schema.json"
        qc_schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validate(instance=qc, schema=qc_schema)
    except ValidationError:
        qc["ok"] = False
        qc["errors"].append("qc.json does not conform to schema")

    qc_path.write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")

    # write outputs into DURUM
    outputs = shot.get("outputs")
    if not isinstance(outputs, dict):
        shot["outputs"] = {}
        outputs = shot["outputs"]

    outputs["qc.json"] = str(qc_path.as_posix())
    if preview_exists:
        outputs["preview.mp4"] = str(preview_path.as_posix())

    durum["last_updated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    Path(durum_path).write_text(json.dumps(durum, ensure_ascii=False, indent=2), encoding="utf-8")

    return _ok(f"{shot_id}: wrote {qc_path}")

