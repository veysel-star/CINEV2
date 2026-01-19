\# CineV3 Architecture



\## 1) Scope

CineV3; shot bazlı üretim akışını (state machine), artifact contract’larını ve doğrulama (validate/transition) kurallarını

dokümante eden ve CineV2 kod tabanına “CineV3 uyumluluğu” ekleyen katmandır.



\## 2) Non-Goals

\- Render motoru / gerçek video üretimi (backend) tasarımı bu dokümanın scope’u değildir.

\- QC karar verme (ok/not ok) mantığını otomatikleştirme scope dışıdır (qc.json sadece contract ile doğrulanır).

\- Dağıtık sistem / multi-repo / cloud deployment bu aşamada yok.



\## 3) Core Entities

\### 3.1 DURUM (CineV3)

\- Root: `project`, `shots`, (opsiyonel) `last\_updated\_utc`

\- `shots`: dictionary; key = shot\_id, value = shot object

\- Shot: `id`, `phase`, `status`, `inputs`, `outputs`, `history`



\### 3.2 Status (State Machine)

CineV3 status seti:

\- PLANNED

\- IN\_PROGRESS

\- QC

\- DONE

\- BLOCKED

\- RETRY

\- FAIL



Terminal:

\- DONE (terminal)

\- FAIL (terminal)



\### 3.3 Artifacts (Outputs)

Bu aşamada authoritative artifact seti:

\- `preview.mp4`

\- `qc.json`



\## 4) Invariants (Hard Rules)

1\) `shots` bir object/dict olmalı (array değil).

2\) Shot key == `shot.id` olmalı (tutarlılık kuralı).

3\) Output path’leri repo altında ve göreli olmalı (absolute path yok).

4\) Bazı geçişler artifact contract’larına bağlıdır (hard gate).

5\) DONE ve FAIL terminaldir (ileri geçiş yok).



\## 5) Contracts

\### 5.1 QC Contract (IN\_PROGRESS -> QC)

\- `outputs\["preview.mp4"]` bulunmalı

\- dosya diskte var olmalı

\- path göreli olmalı (repo altında)



\### 5.2 DONE Contract (QC -> DONE)

\- `outputs\["preview.mp4"]` bulunmalı ve diskte var olmalı

\- `outputs\["qc.json"]` bulunmalı ve diskte var olmalı

\- `qc.json` schema doğrulamasından geçmeli (repo `schema/qc.schema.json`)

\- `qc.json` semantik koşul:

&nbsp; - `ok: true`

&nbsp; - `errors: \[]` (boş liste)



\## 6) CLI Responsibilities (CineV3)

\### 6.1 validate

\- CineV2 ve CineV3 formatını ayırt eder

\- CineV3 için `schema/cinev3/durum.schema.json` ile tüm dokümanı doğrular

\- `qc.json` varsa `schema/qc.schema.json` ile doğrular (hardening)



\### 6.2 transition

\- Only-authoritative transition table uygular

\- QC ve DONE geçişlerinde hard gate uygular (contract)

\- Terminal durumlara ileri geçişi engeller (DONE/FAIL)



\## 7) Directory Layout

\- `docs/cinev3/` : CineV3 dokümantasyon

\- `docs/cinev3/decisions/` : tasarım kararları (ADR)

\- `schema/cinev3/durum.schema.json` : CineV3 DURUM schema

\- `schema/qc.schema.json` : qc.json schema (CineV2/CineV3 ortak)

\- `tools/cli/validate.py` : format routing + schema validate

\- `tools/cli/transition.py` : transition gate + qc schema enforcement



\## 8) Decision Records (ADR)

Bu repo içinde tasarım kararları `docs/cinev3/decisions/` altında tutulur.

Her karar:

\- Context

\- Decision

\- Consequences

\- Alternatives (neden seçilmedi)



Index: `docs/cinev3/decisions/README.md`



\## 9) Versioning

\- CineV3 değişiklikleri PR ile master’a alınır.

\- Master üzerinde tag (CINEV2\_v0.xx) ile sürümleme yapılır.



