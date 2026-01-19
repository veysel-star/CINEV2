\# ADR-0002: Shot V4 Required Fields



\## Context



CineV3 shot modeli minimumdu.

Artifact ve release bağı zayıftı.



\## Decision



CineV4 shot modeli şunları zorunlu kılar:

\- id

\- status

\- version

\- artifacts

\- manifest\_ref



\## Consequences



\+ Shot tek başına doğrulanabilir

\+ Release otomatikleşir

\- Eski CineV3 shot’lar upgrade ister



