\# CineV4 Architecture



\## 1. High-Level Overview



CineV4 mimarisi \*\*contract-first\*\* ve \*\*immutable-output\*\* prensibine dayanır.



Her aşama:

\- Girdi alır

\- Çıktı üretir

\- Manifest ile sabitlenir

\- Hash ile doğrulanır



---



\## 2. Core Layers



\### 2.1 Project Layer



\- `project.json`

\- Projenin kimliği, versiyonu, policy’leri

\- Shot’ların üst bağlamı



\### 2.2 Shot Layer (CineV4 Shot)



\- CineV3 shot modelinin devamı

\- Ek alanlar:

&nbsp; - version

&nbsp; - artifacts (liste)

&nbsp; - manifest\_ref



\### 2.3 Artifact Layer



\- Fiziksel dosyalar (mp4, qc.json, logs)

\- Her artifact:

&nbsp; - relative path

&nbsp; - size

&nbsp; - hash (sha256)



\### 2.4 Manifest Layer



\- `manifest.json`

\- Shot + artifact + hash ilişkisini sabitler

\- Release’in tek doğrulama kaynağıdır



\### 2.5 Release Layer



\- Release sadece:

&nbsp; - DONE state

&nbsp; - geçerli manifest

&nbsp; - hash doğrulaması

&nbsp; ile mümkündür



---



\## 3. Data Flow



1\. Shot üretimi (IN\_PROGRESS)

2\. QC (QC)

3\. DONE → manifest oluşturulur

4\. Manifest hash’lenir

5\. Release gate çalışır

6\. Release publish edilir



---



\## 4. Failure Model



\- DONE sonrası \*\*geri dönüş yok\*\*

\- Manifest bozulursa release invalid

\- Hash mismatch = FAIL



---



\## 5. Guarantees



CineV4 şunu garanti eder:

\- Aynı manifest → aynı çıktı

\- Hash tutmuyorsa sistem durur

\- “Elimde çalışıyordu” durumu yoktur



