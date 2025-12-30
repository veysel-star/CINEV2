# CINEV2

CINEV2 is a clean rewrite. CINEV1 is kept as a read-only reference remote (`cinev1`), frozen at tag `CINEV1_v1.0`.

Goal of CINEV2:
- Keep the proven release discipline (MASTER/PROJECT, SHA256, DELIVERY)
- Replace "fake finalize" with real production steps (renderer integration later)
- Stronger state machine + validation + reproducible packaging

## Workflow (strict)

- `master` is protected: no direct pushes.
- All changes happen via PR:
  1) create a branch
  2) commit
  3) push branch
  4) open PR
  5) merge

## Tags

- Baseline: `CINEV2_v0.1` (pipeline rules locked)
- New versions use new tags: `CINEV2_v0.2`, `CINEV2_v0.3`, ...
