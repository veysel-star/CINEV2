\# ADR-0004: QC->DONE requires qc.schema.json + ok:true + errors:\[]



\## Context

DONE statüsü release gate için güvenilir olmalı. Sadece dosya varlığı yeterli değil.



\## Decision

QC->DONE geçişi hard gate:

\- qc.json dosyası var olmalı

\- qc.schema.json ile doğrulanmalı

\- semantik: ok=true ve errors=\[]



\## Consequences

\- DONE “release-ready” anlamına gelir.

\- QC raporu bozuksa state machine izin vermez.



\## Alternatives

\- Sadece file exists: kalite kriteri yok.

\- ok alanını kontrol etmemek: QC fail durumları DONE’a sızar.



