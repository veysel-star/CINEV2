# References

CINEV1 reference remote:
- remote: cinev1
- tag: CINEV1_v1.0

Useful commands:
- git show CINEV1_v1.0:docs/CINEV1_PIPELINE_RULES.md
- git log cinev1/master --oneline

## CLI contracts

### render
Contract:
- Input: --src points to an existing source preview.mp4
- Output: writes <out>/preview.mp4 (copy or generated preview)
- State update: DURUM.shots[SHOT_ID].outputs["preview.mp4"] is stored as a RELATIVE path
  (example: "outputs/v0008/preview.mp4"), not an absolute machine path.
- Exit code: 0 on success; non-zero on failure.
- This command is intended for local execution (not CI).


