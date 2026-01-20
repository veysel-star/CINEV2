# CineV4 Architecture



## 1. High-Level Overview



CineV4 mimarisi **contract-first** ve **immutable-output** prensibine dayanır.



Her aşama:

- Girdi alır

- Çıktı üretir

- Manifest ile sabitlenir

- Hash ile doğrulanır



---



## 2. Core Layers



### 2.1 Project Layer

- `project.json` (project-level contract)

Minimum alanlar (MUST):
- `id` (string, boş olamaz)
- `version` (string, ör: "v4")
- `created_utc` (ISO-8601 UTC, Z ile)
- `policy` (object)

`policy` minimum alanlar (MUST):
- `hash_alg` (string enum: "sha256")
- `path_mode` (string enum: "relative")  # tüm artifact path'leri project root'a göre relatif
- `immutable_outputs` (boolean): strict-mode/policy ile kontrol edilir.   
   - true: DONE sonrası artifact değişemez (immutability)
   - false: kontrollü şekilde yeniden üretim yapılabilir; bu durumda yeni manifest üretilir ve hash'ler değiştiği için "eski manifest" artık o release için geçerli olmaz (yeni manifest = yeni kimlik/versiyon).
   - Not: immutable_outputs davranışı strict-mode policy tarafından belirlenir; normatif tanım ADR-0004 (done-strict-mode).
- `done_requires_manifest` (boolean, true)

Opsiyonel alanlar (MAY):
- `name`, `description`
- `owner`, `tags`




### 2.2 Shot Layer (CineV4 Shot)



- CineV3 shot modelinin devamı

- Ek alanlar:

  - version

  - artifacts (liste)

  - manifest_ref



### 2.3 Artifact Layer

- Fiziksel dosyalar (mp4, qc.json, logs)

Her artifact (MUST):
- `path` (string, relative; ör: "outputs/v0001/preview.mp4")
- `size` (integer, bytes)
- `sha256` (string, 64 hex)

Opsiyonel (MAY):
- `media_type` (ör: "video/mp4", "application/json")
- `role` (ör: "preview", "qc", "log")




### 2.4 Manifest Layer

- `manifest.json` (authoritative verification source)

Manifest minimum alanlar (MUST):
- `schema` (string, ör: "cinev4/manifest@1")
- `project_id` (string)
- `shot_id` (string)
- `created_utc` (ISO-8601 UTC, Z ile)
- `hash_alg` (string enum: "sha256")
- `artifacts` (array, min 1)

`artifacts[]` elemanı (MUST):
- `path` (string, relative)
- `size` (integer)
- `sha256` (string)

Manifest kuralları (MUST):
- Manifest içeriği ile disk üzerindeki dosyaların `size` ve `sha256` değeri eşleşmelidir.
- Manifest oluşturulduktan sonra değiştirilemez (immutable).




### 2.5 Release Layer



- Release sadece:

  - DONE state

  - geçerli manifest

  - hash doğrulaması

  - ile mümkündür



---



## 3. Data Flow

1. Shot üretimi (IN_PROGRESS)
2. QC (QC)
3. QC->DONE geçişi için qc.json + preview gibi çıktılar hazır olmalıdır (CineV3 gate devam eder)
4. Manifest üretimi (MUST): `tools.cli` tarafından (örn. `python -m tools.cli manifest ...`) manifest.json yazılır
5. Release gate manifest'i doğrular (hash/size/path)
6. Release publish edilir




## 4. Failure Model

### 4.1 Shot-level FAIL (runtime / production)
- Shot üretiminde teknik hata (render crash, missing input vb.) => shot `status=FAIL`
- FAIL terminaldir (geri dönüş yok) [policy strict ise]

### 4.2 Release-gate FAIL (verification)
- Manifest var ama doğrulama geçmiyor (sha256/size/path mismatch) => release gate FAIL
- Bu, shot status'unu otomatik FAIL yapmaz (ayrı mekanizma)
- Release publish edilmez




## 5. Guarantees



CineV4 şunu garanti eder:

- Aynı manifest → aynı çıktı

- Hash tutmuyorsa sistem durur

- “Elimde çalışıyordu” durumu yoktur



