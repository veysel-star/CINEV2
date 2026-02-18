# CineV4 Scope



## 1) Purpose



CineV4, CineV3’ün “shot lifecycle + contract” yaklaşımını tek şottan çıkarıp **proje seviyesine** taşır.



Hedef: Bir projenin (film/episode) üretilmesini, versiyonlanmasını ve yayınlanabilir bir “release”e dönüşmesini

tek bir doğrulanabilir sözleşme (contract) seti ile yönetmek.



CineV4; CineV2 repo’su içinde:

- Proje manifest’i,

- Hash/immutability,

- Multi-shot bağımlılıkları,

- Strict-mode release gating

katmanını tanımlar ve dokümante eder.





## 2) In Scope (CineV4’de var)



### 2.1 Project-level contract

- Proje tanımı (project id, metadata, assets, shots list)

- Shot’ların proje içinde referanslanması ve bağlanması

- “Ne üretildi / hangi dosya nereye yazıldı” bilgisinin proje bazında toplanması



### 2.2 Manifest + Hashes (immutability)

- Üretilen artifact’lar için deterministik manifest

- Dosya hash’leri (en az SHA256) ile “bu çıktı değişmedi” garantisi

- “Yayınlanabilir set” = manifest + hash + minimum metadata



### 2.3 Strict-mode release gate

- Release çıkarma, yalnızca kurallar sağlanıyorsa mümkün:

  - Tüm required shot’lar terminal (DONE/FAIL politikası ADR ile)

  - QC gereklilikleri sağlanmış

  - Manifest + hash’ler üretilmiş / doğrulanmış

- “Release üretimi” bir komut/flow olarak tanımlanır (CI tarafından da koşabilir)



### 2.4 Multi-shot orchestration (minimal)

- “Hangi shot’lar bu release’e dahil”

- Shot bağımlılıkları (ör: SH010, SH009 tamamlanmadan done sayılmasın gibi) sadece manifest seviyesinde



> Not: CineV4, render backend’i eklemek zorunda değildir.

> Render “output üreten dış süreç” olarak kabul edilir; CineV4 onun çıktısını contract/hashes ile kilitler.





## 3) Non-Goals (CineV4’de yok)



- Render motoru / video üretim backend’i (Blender/Unreal/FFmpeg pipeline) tasarımı

- Otomatik QC karar verme (model ile ok/not ok üretme). QC sadece contract doğrulaması + dosya varlığı/hashes

- Dağıtık sistem, cloud orchestration, multi-repo mimari

- UI / web panel / prod ortam deploy





## 4) Inputs / Outputs



### Inputs (minimum)

- CineV3 uyumlu DURUM (shot states + outputs)

- Proje tanımı / manifest girdisi (dosya)

- Outputs klasörü (artifact’ların bulunduğu ağaç)



### Outputs (minimum)

- `project.json` veya `manifest.json` (proje + release içeriği)

- `manifest.sha256` veya manifest içinde `sha256` alanları

- Release klasörü (versiyonlu): ör. `releases/<rel\_id>/...`




## 4.1 Production Contract (CineV4)

- Üretim birimi: **shot**
- Çıktı standardı (minimum):
  - `outputs/<shot_id>/<vXXXX>/preview.mp4`
  - `outputs/<shot_id>/<vXXXX>/qc.json`
- Gate sırası (authoritative):
  - `IN_PROGRESS -> QC -> DONE -> RELEASE`
- DONE şartları (hard gate):
  - `qc.json` içinde `ok == true`
  - `preview.mp4` disk üzerinde mevcut
  - output path’leri **relative**, **traversal yok**, repo kökü altında
- RELEASE şartları (hard gate):
  - `manifest.json` + `sha256` doğrulaması
  - bundle verify PASS

  


## 5) Compatibility



- CineV4, CineV3 shot contract’ını \*\*bozmaz\*\*; üstüne proje katmanı koyar.

- CineV3’te `qc.json`/`preview.mp4` gibi contract’lar CineV4 release gating’in girdisidir.

- “CineV4 yoksa CineV3 çalışır”; CineV4 opsiyonel üst katmandır.



## 6) Success Criteria



CineV4 tamamlandı sayılması için minimum şartlar:

- Proje manifest formatı tanımlı ve dokümante

- Hash politikası tanımlı ve CI’da doğrulanabilir

- Strict-mode release gate kuralları ADR’lerle kilitli

- Örnek bir demo proje ile “manifest + hashes + release gate” uçtan uca çalıştığı kanıtlı





## 7) Related Docs



- `docs/cinev4/ARCHITECTURE.md`

- `docs/cinev4/decisions/README.md`

- ADR-0001..0004 (bu klasörde)



