# BUNDLE – Çoklu Release Birleştirme Tasarımı

## Amaç
Birden fazla mevcut release klasörünü tek bir “bundle release” altında birleştirmek.
Bundle kaynak release’leri değiştirmez (read-only).

## CLI
python -m tools.cli bundle --sources <r1> <r2> ... [--bundle-id ID]

Parametreler:
- --sources   : Birleştirilecek release klasörleri (en az 1)
- --bundle-id : Opsiyonel; verilmezse UTC timestamp

## Manifest
- manifest_version: 3
- hash_alg: sha256
- release_id: <bundle_id>
- kind: bundle
- sources: (source_release_id, source_manifest_sha256, source_path)
- shots: (shot_id, source_release_id, files[])
- totals

## Çakışma Politikası
Aynı shot birden fazla kaynakta varsa default: FAIL.

## PASS
- releases/<bundle_id>/manifest.json var
- tüm dosyalar var
- SHA256 eşleşiyor
- verify-manifest PASS


