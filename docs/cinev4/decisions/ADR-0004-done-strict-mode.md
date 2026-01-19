\# ADR-0004: DONE Strict Mode



\## Context



DONE state sonrası dosya değişimi sistemde belirsizlik yaratır.



\## Decision



CineV4’te:

\- DONE state terminaldir

\- DONE sonrası:

&nbsp; - dosya eklenemez

&nbsp; - dosya değiştirilemez

&nbsp; - manifest değiştirilemez



\## Consequences



\+ Güçlü release disiplini

\+ Deterministic pipeline

\- Hata düzeltme yeni shot/version gerektirir



