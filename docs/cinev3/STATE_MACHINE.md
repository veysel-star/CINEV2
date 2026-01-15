# CineV3 State Machine

## 1) Amaç
CineV3 üretim akışı, her shot için tek bir durum (status) üzerinden yönetilir. Durum geçişleri sadece izinli kurallarla yapılır ve bazı geçişler belirli dosya/artefact şartlarına bağlıdır.

## 2) Status (Durumlar)
Aşağıdaki status’lar CineV3’te geçerlidir:

- PLANNED
- IN_PROGRESS
- QC
- DONE
- BLOCKED
- RETRY
- FAIL

## 3) Status Anlamları (Semantik)
- PLANNED: Shot tanımlı, üretime başlanmamış.
- IN_PROGRESS: Üretim başladı; çıktılar eksik/ara aşamada olabilir.
- QC: Kalite kontrol aşaması; QC artefact’ı oluşmuş olmalı.
- DONE: Üretim tamamlandı; release gate’i geçecek şekilde gerekli artefact’lar mevcut olmalı.
- BLOCKED: Harici engel var (asset eksik, bağımlılık, karar bekleme vb.). İlerleyemez.
- RETRY: Üretimde hata/uygunsuzluk oldu; tekrar IN_PROGRESS’a dönüp yeniden üretim yapılacak.
- FAIL: Shot iptal/başarısız; terminal kabul edilir (ileriye geçiş yok).

## 4) Zorunlu Artefact Contract’ları
Bu contract’lar sağlanmadan bazı geçişler yapılmaz.

### 4.1 QC için
QC statüsüne geçişte şunlar zorunludur:
- outputs["preview.mp4"] mevcut olmalı
- bu dosya disk üzerinde bulunmalı (repo altında, göreli path)

### 4.2 DONE için
DONE statüsüne geçişte şunlar zorunludur:
- outputs["preview.mp4"] mevcut olmalı
- outputs["qc.json"] mevcut olmalı
- her ikisi de disk üzerinde bulunmalı (repo altında, göreli path)

## 5) İzinli Geçişler (Authoritative Transition Table)
Aşağıdaki tablo “tek doğru” geçiş setidir.

### 5.1 Normal üretim akışı
- PLANNED -> IN_PROGRESS
- IN_PROGRESS -> QC          (QC contract: preview.mp4 zorunlu)
- QC -> DONE                 (DONE contract: preview.mp4 + qc.json zorunlu)

### 5.2 Alternatif/istisna geçişler (kontrollü)
- IN_PROGRESS -> BLOCKED
- BLOCKED -> IN_PROGRESS
- QC -> RETRY
- RETRY -> IN_PROGRESS
- IN_PROGRESS -> FAIL
- QC -> FAIL
- RETRY -> FAIL
- BLOCKED -> FAIL

### 5.3 Terminal durumlar
- DONE: terminal (ileri geçiş yok)
- FAIL: terminal (ileri geçiş yok)

## 6) Açıkça Yasak Geçişler (Örnekler)
Bu liste tam değil; tablo dışındaki her şey yasaktır.

- DONE -> IN_PROGRESS (yasak)
- DONE -> QC (yasak)
- FAIL -> herhangi bir şey (yasak)
- PLANNED -> QC (yasak)
- PLANNED -> DONE (yasak)
- BLOCKED -> QC (yasak)
- BLOCKED -> DONE (yasak)

## 7) CineV3’ün Yapmayacağı Şeyler (Non-Goals)
- Otomatik status atlama yapmaz (ör. QC’siz DONE yok).
- Otomatik “retry sayacı” veya otomatik tekrar deneme yürütmez (RETRY sadece durumdur).
- QC sonuçlarını yorumlayıp karar vermez (qc.json üretir/varlığını şart koşar, yorum dışarıda).
- Repo dışına output yazmaz (tüm output path’leri repo altında, göreli olmalıdır).

## 8) CLI Sorumlulukları (Belge Seviyesi)
CineV3 CLI şunları sağlamalıdır:
- Geçişler sadece bu tabloya göre yapılır.
- QC ve DONE geçişlerinde contract kontrolü yapılır.
- Output path’leri repo altında ve göreli olmalıdır (absolute path yasak).
