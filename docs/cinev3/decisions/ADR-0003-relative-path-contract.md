\# ADR-0003: Relative path contract (repo altında output)



\## Context

Output path’leri bazen repo dışına yazılabilir. Bu CI ve portability için sorun.



\## Decision

Output path’leri:

\- göreli olacak

\- repo root altında kalacak



\## Consequences

\- CI stateless çalışır.

\- Release/validate geçerli ve taşınabilir olur.



\## Alternatives

\- Absolute path serbest: makine bağımlılığı üretir.

\- Repo dışı çalışma klasörü: release toplama güvenilmezleşir.



