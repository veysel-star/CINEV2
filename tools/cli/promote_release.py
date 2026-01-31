import argparse, json, os
from datetime import datetime, timezone


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _fail(msg: str) -> int:
    print(f"[ERR] {msg}")
    return 2


def _read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _parse_shots_any(value):
    """
    Accept:
      --shots SH001 SH002        -> ["SH001","SH002"]
      --shots SH001,SH002        -> ["SH001","SH002"]
      --shots SH001 SH002,SH003  -> ["SH001","SH002","SH003"]
    """
    out = []
    if value is None:
        return out

    if isinstance(value, (list, tuple)):
        items = value
    else:
        items = [value]

    for item in items:
        if item is None:
            continue
        for part in str(item).split(","):
            sid = part.strip()
            if sid:
                out.append(sid)
    return out


def cmd_promote_release(args) -> int:
    path = args.path
    project_id = args.project
    release_id = args.release

    if not project_id:
        return _fail("missing --project")
    if not release_id:
        return _fail("missing --release")

    try:
        durum = _read_json(path)
    except Exception as e:
        return _fail(f"cannot read {path}: {e}")

    shots = durum.get("shots") or {}
    if not isinstance(shots, dict):
        return _fail("DURUM.json: shots must be an object")

    # selection
    if args.all_done:
        selected = [sid for sid, sh in shots.items() if isinstance(sh, dict) and sh.get("status") == "DONE"]
    else:
        selected = _parse_shots_any(args.shots)
        if not selected:
            return _fail("--shots is empty")

        missing = [sid for sid in selected if sid not in shots]
        if missing:
            return _fail("shot not found: " + ", ".join(missing))

    if not selected:
        return _fail("no shots selected")

    # Gate FIRST (fail-fast; do not touch DURUM if gate fails)
    from .release_gate import main as release_gate
    release_gate(["--project", project_id, "--release", release_id])

    # Promote
    now = _utc_now_z()
    promoted = 0

    for sid in selected:
        sh = shots.get(sid)
        if not isinstance(sh, dict):
            return _fail(f"{sid}: invalid shot record")

        cur = sh.get("status")

        # idempotent: zaten RELEASE ise dokunma, devam et
        if cur == "RELEASE":
            continue

        # DONE değilse yine fail et (QC/IN_PROGRESS/PLANNED vb. yanlış)
        if cur != "DONE":
            return _fail(f"{sid}: must be DONE to promote (current: {cur})")

        sh["status"] = "RELEASE"
        sh.setdefault("history", []).append(
            {
                "event": "STATUS_CHANGED",
                "from": "DONE",
                "to": "RELEASE",
                "at": now,
                "by": "cli",
            }
        )
        promoted += 1

    durum["last_updated_utc"] = now

    try:
        _write_json(path, durum)
    except Exception as e:
        return _fail(f"cannot write {path}: {e}")

    print("[OK] promoted shots:", promoted)
    print("[OK] release:", release_id)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tools.cli promote-release", add_help=True)
    ap.add_argument("path", help="Path to DURUM.json")
    ap.add_argument("--project", required=True, help="Project id (e.g. demo01)")
    ap.add_argument("--release", required=True, help="Release id (e.g. demo01_r0005)")

    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all-done", action="store_true", help="Promote all DONE shots")
    g.add_argument("--shots", nargs="+", help="Shot ids (e.g. SH001 SH002) or SH001,SH002")

    args = ap.parse_args(argv)
    raise SystemExit(cmd_promote_release(args))


if __name__ == "__main__":
    main()
