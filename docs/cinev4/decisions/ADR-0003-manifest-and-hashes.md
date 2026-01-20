# ADR-0003: Manifest and Hashes



## Context



Dosya varlığı tek başına güvenli değildir.

İçeriğin değişmediği garanti edilmelidir.


## Decision



- Her artifact için sha256 hash zorunlu

- Manifest bu hash’leri authoritative source olarak taşır



## Consequences



+ Reproducibility sağlanır

+ Release doğrulanabilir

- Hash üretimi ek maliyet getirir



