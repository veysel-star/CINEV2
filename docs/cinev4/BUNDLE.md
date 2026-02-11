# BUNDLE – Çoklu Release Birleştirme Tasarımı

## Amaç

Birden fazla mevcut release klasörünü tek bir "resmi bundle release" altında birleştirmek.

Bundle:
- Kaynak release’leri değiştirmez (read-only)
- Yeni bir release klasörü üretir
- Tek başına doğrulanabilir manifest üretir
- Verify + Release Gate PASS olmadan tamamlanmış sayılmaz

---

## CLI Arayüzü

Yeni komut:

    cinev bundle --sources <r1> <r2> [...] [--bundle-id ID] [--shots SH001,SH002] [--prefer latest]

Parametreler:

- --sources       : Birleştirilecek release klasörleri
- --bundle-id     : Opsiyonel; verilmezse UTC timestamp
- --shots         : Belirli shot’ları dahil et
- --prefer latest : Çakışma durumunda en yeni release'i seç (default: fail)

---

## Manifest Yapısı

manifest_version: 3
release_id: <bundle_id>
kind: "bundle"

sources:
- source_release_id
- source_manifest_sha256
- source_path

shots:
- shot_id
- source_release_id
- files:
    - preview.mp4
    - qc.json
    - sha256
    - bytes

totals:
- total_shots
- total_files
- total_bytes

---

## Çakışma Politikası

Eğer aynı shot birden fazla kaynak release’te varsa:

Default:
    FAIL (güvenli)

Opsiyonel:
    --prefer latest

---

## PASS Kriteri

Bundle başarılı sayılması için:

1. releases/<bundle_id>/manifest.json var
2. Listedeki tüm dosyalar fiziksel olarak var
3. SHA256 değerleri eşleşiyor
4. verify-manifest PASS
5. release-gate PASS

Bu koşullar sağlanmazsa bundle resmi sayılmaz.
