\# ADR-0005: Terminal states (DONE/FAIL) are strictly terminal



\## Context

DONE’a geçmiş shot’ın tekrar üretime dönmesi veya FAIL’den çıkması state machine’i belirsizleştirir.



\## Decision

\- DONE terminaldir: ileri geçiş yok

\- FAIL terminaldir: ileri geçiş yok



\## Consequences

\- Akış deterministik kalır.

\- Geri dönüş gerekiyorsa yeni shot/versiyon mantığıyla yapılır (state override yok).



\## Alternatives

\- DONE’dan geri dönmek: release bütünlüğünü bozar.

\- FAIL’den çıkmak: hata takibini belirsizleştirir.



