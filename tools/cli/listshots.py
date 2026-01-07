import json
from pathlib import Path


def _fail(msg: str) -> int:
    print(f"[ERR] {msg}")
    return 2


def _safe_str(x):
    if x is None:
        return ""
    return str(x)


def cmd_listshots(args) -> int:
    durum_path = Path(args.path)

    if not durum_path.exists() or not durum_path.is_file():
        return _fail(f"cannot read {durum_path}")

    try:
        durum = json.loads(durum_path.read_text(encoding="utf-8"))
    except Exception as e:
        return _fail(f"invalid json: {e}")

    shots = durum.get("shots")
    if not isinstance(shots, dict):
        return _fail("DURUM.json: 'shots' must be an object")

    # collect
    rows = []
    for sid, shot in shots.items():
        if not isinstance(shot, dict):
            continue

        status = shot.get("status", "")
        phase = shot.get("phase", "")
        prompt = ""
        inputs = shot.get("inputs") or {}
        if isinstance(inputs, dict):
            prompt = inputs.get("prompt", "")

        outputs = shot.get("outputs") or {}
        out_count = len(outputs) if isinstance(outputs, dict) else 0

        rows.append(
            {
                "id": _safe_str(sid),
                "phase": _safe_str(phase),
                "status": _safe_str(status),
                "out_count": out_count,
                "prompt": _safe_str(prompt),
            }
        )

    # filters (optional)
    if args.status:
        rows = [r for r in rows if r["status"] == args.status]
    if args.phase:
        rows = [r for r in rows if r["phase"] == args.phase]

    # sort by id
    rows.sort(key=lambda r: r["id"])

    # table header
    print(f"{'ID':<8} {'PHASE':<8} {'STATUS':<12} {'OUT#':<5} PROMPT")
    print("-" * 80)

    for r in rows:
        p = r["prompt"].replace("\n", " ").strip()
        if len(p) > 60:
            p = p[:57] + "..."
        print(f"{r['id']:<8} {r['phase']:<8} {r['status']:<12} {str(r['out_count']):<5} {p}")

    # summary (total is ALL shots, not filtered)
    total = len([1 for _, v in shots.items() if isinstance(v, dict)])
    done = len([1 for _, v in shots.items() if isinstance(v, dict) and v.get("status") == "DONE"])
    print("")
    print(f"TOTAL shots: {total} | DONE: {done}")

    return 0
