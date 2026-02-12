# BUNDLE – Çoklu Release Birleştirme Tasarımı

## Amaç
Birden fazla mevcut release klasörünü tek bir “bundle release” altında birleştirmek.
Bundle kaynak release’leri değiştirmez (read-only).

## CLI
python -m tools.cli bundle --sources <r1> <r2> ... [--bundle-id ID]

## Parametreler
- --sources : Birleştirilecek release klasörleri (en az 1)
- --bundle-id : Opsiyonel; verilmezse UTC timestamp
- --shots : Opsiyonel; virgülle ayrılmış shot id listesi (örn: SH041,SH042)
- --prefer : Çakışma çözüm politikası (default: fail) {fail, latest}


## Manifest
- manifest_version: 3
- hash_alg: sha256
- release_id: <bundle_id>
- kind: bundle
- sources: (source_release_id, source_manifest_sha256, source_path)
- shots: (shot_id, source_release_id, files[])
- totals

## Çakışma Politikası
Aynı shot birden fazla kaynakta varsa:

- Default: FAIL
  - bundle komutu hata verir ve durur.

- --prefer latest
  - Kaynak manifest’lerdeki created_utc alanına bakar
  - En yeni release’i seçer
  - Uyarı (WARN) basar ve devam eder


## PASS
- releases/<bundle_id>/manifest.json var
- tüm dosyalar var
- SHA256 eşleşiyor
- verify-manifest PASS

## Örnekler

### Çakışmada FAIL (default)
python -m tools.cli bundle --sources releases/A releases/B --bundle-id TEST_BUNDLE_FAIL
# Aynı shot iki kaynakta varsa:
# [FAIL] duplicate shot SH041 in sources ...

### Çakışmada LATEST seç (warn + devam)
python -m tools.cli bundle --sources releases/A releases/B --bundle-id TEST_BUNDLE_LATEST --prefer latest
# Aynı shot iki kaynakta varsa:
# [WARN] duplicate SH041 -> picking <release_id> (latest), ignoring <release_id>



