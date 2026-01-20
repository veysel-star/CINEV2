# ADR-0004: DONE Strict Mode



## Context



DONE state sonrası dosya değişimi sistemde belirsizlik yaratır.



## Decision

- Bu karar, project.policy.immutable_outputs == true durumunda uygulanan strict-mode davranışını tanımlar.

When immutable_outputs == false:
- DONE artifacts MAY be regenerated.
- Regeneration MUST produce a new manifest.
- New manifest represents a new version/identity.
- This rule applies at release level; individual shots MUST NOT bypass this constraint.




CineV4’te:

- DONE state MUST be terminal.
  After DONE:

  - Artifacts MUST NOT be added.

  - Artifacts MUST NOT be modified.

  - manifest.json MUST NOT be changed.




## Consequences



+ Güçlü release disiplini

+ Deterministic pipeline

- Hata düzeltme yeni manifest üretimini gerektirir.

- Bu yeni manifest, önceki release için geçerli değildir.



