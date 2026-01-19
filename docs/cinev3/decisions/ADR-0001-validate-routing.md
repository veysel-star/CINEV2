\# ADR-0001: CineV3 DURUM format detection in CLI validate



\## Context

CLI `validate` hem CineV2 DURUM.json formatını hem CineV3 formatını desteklemelidir.



\## Decision

`tools/cli/validate.py` içinde dosya bir kere yüklenir ve top-level alanlara göre format seçilir:

\- CineV2: active\_project, current\_focus, last\_updated\_utc

\- CineV3: project, shots



\## Consequences

\- Tek komutla iki format doğrulanabilir.

\- Hatalı formatlarda net hata mesajı üretilebilir.



\## Alternatives

\- Ayrı komutlar (validate-v2 / validate-v3): kullanıcı akışını böler.

\- Dosya adına göre ayrım: güvenilir değil.



