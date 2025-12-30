# CINEV2 – Pipeline Rules (Authoritative)

## 1. Purpose
CINEV2 is a clean rewrite.
CINEV1 is frozen and used only as a read-only historical reference.

This repository enforces a strict, reproducible production pipeline.
No demo shortcuts, no fake finalization.

---

## 2. Repository Policy
- `master` branch is protected and immutable by direct push
- All changes must go through pull requests
- Force push and branch deletion are forbidden

---

## 3. Versioning Rules
- Pre-release: v0.x (architecture and pipeline only)
- Stable release: v1.0+
- Every release MUST have:
  - Git tag
  - GitHub Release
  - SHA256 checksum
  - DELIVERY manifest

---

## 4. Production Model
CINEV2 enforces a real production flow:

PLANNING → BRIEF → PRODUCTION → QC → RELEASE

Skipping steps is not allowed.

---

## 5. Fake Finalization Policy
The following are explicitly forbidden:
- Marking outputs as final without real generation
- Placeholder renders marked as releases
- Manual tampering with release artifacts

---

## 6. Reference
CINEV1 is available as a frozen reference only:
- Remote: cinev1
- Tag: CINEV1_v1.0

No code or structure is copied blindly.

## 7. Shot Status Transition Rules

A shot MUST follow this exact lifecycle:

PLANNED → IN_PROGRESS → DONE

### PLANNED → IN_PROGRESS
Allowed only if:
- `inputs` is NOT empty
- A planning decision is recorded in `history`

### IN_PROGRESS → DONE
Allowed only if:
- `outputs` is NOT empty
- All required artifacts are present
- A completion event is recorded in `history`

### Forbidden
- Skipping any phase
- Reverting status backwards
- Marking DONE without real outputs

