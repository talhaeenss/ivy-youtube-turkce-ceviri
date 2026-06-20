<h1 align="center">🎬 YouTube Türkçe Çeviri & Dublaj</h1>

<p align="center">
  YouTube videolarını (veya herhangi bir video dosyasını) yapay zeka ile otomatik olarak<br />
  <strong>İngilizce'den Türkçe'ye çevirip, doğal sesle dublajlayan</strong> yerel masaüstü uygulaması.
</p>

<p align="center">
  <code>Konuşma Tanıma (Whisper)</code> → <code>Çeviri (Google Translate)</code> → <code>Seslendirme (Supertonic TTS)</code> → <code>MP4 Çıktı</code>
</p>

<p align="center">
  <img src="[https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge&logo=python&logoColor=white](https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge&logo=python&logoColor=white)" />
  <img src="[https://img.shields.io/badge/FastAPI-2.0-009688?style=for-the-badge&logo=fastapi&logoColor=white](https://img.shields.io/badge/FastAPI-2.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)" />
  <img src="[https://img.shields.io/badge/Whisper-AI-ff6f00?style=for-the-badge&logo=openai&logoColor=white](https://img.shields.io/badge/Whisper-AI-ff6f00?style=for-the-badge&logo=openai&logoColor=white)" />
  <img src="[https://img.shields.io/badge/Supertonic-TTS-9C27B0?style=for-the-badge&logo=onnx&logoColor=white](https://img.shields.io/badge/Supertonic-TTS-9C27B0?style=for-the-badge&logo=onnx&logoColor=white)" />
</p>

---

## 📖 Ne İşe Yarar?

Bu proje, İngilizce konuşulan bir videoyu alır ve aşağıdaki pipeline ile **tam otomatik Türkçe dublaj** üretir:

1. **Konuşma Tanıma** — [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2, int8 quantize) ile videonun sesini metne çevirir. CPU'da orijinal Whisper'a göre **~4x hızlıdır**.
2. **Çeviri** — İngilizce metni Türkçe'ye çevirir. Üç katmanlı fallback: LibreTranslate (lokal) → Google Translate (hızlı API) → deep-translator.
3. **Seslendirme (TTS)** — **Supertonic** ile yerel (cihaz üzerinde), ONNX tabanlı, 99M parametreli açık ağırlıklı model kullanılarak yüksek kaliteli (44.1kHz) ve yıldırım hızında Türkçe ses üretir. Bulut veya internet bağlantısı gerektirmez, cihazınızda çalışır.
4. **Video Birleştirme** — ffmpeg ile orijinal videonun görüntüsü + yeni Türkçe ses birleştirilerek **dublajlı MP4** çıktısı oluşturulur.

### ✨ Öne Çıkan Özellikler

| Özellik | Açıklama |
|---------|----------|
| 🌐 **YouTube desteği** | `yt-dlp` ile doğrudan YouTube bağlantısından video indirir |
| 📂 **Dosya yükleme** | Bilgisayarınızdaki videoları da işleyebilir |
| ⚡ **Hızlı mod** | faster-whisper (int8) + VAD filtresi ile sessiz kısımlar atlanır |
| 🎛️ **Ayarlanabilir hız** | TTS konuşma hızı: Normal (+0%) ile Çok Hızlı (+80%) arası |
| 🖥️ **Web paneli** | Retro-futurist CRT temalı modern arayüz |
| 📡 **REST API** | Swagger dokümantasyonu ile programatik erişim |
| 🔄 **İş kuyruğu** | Arka planda asenkron işleme, ilerleme takibi |
| 🚀 **Tek tuşla kurulum** | `run-local.bat` — venv, pip, bağımlılıklar otomatik |

---

## 🔧 Gereksinimler

| Bileşen | Minimum Versiyon | Açıklama |
|---------|-----------------|----------|
| **Python** | 3.13+ | [python.org](https://python.org) — `py` launcher kurulu olmalı |
| **ffmpeg** | — | Otomatik: `imageio-ffmpeg` paketi ile gelir. İsterseniz [ffmpeg.org](https://ffmpeg.org)'dan da kurabilirsiniz |
| **yt-dlp** | — | `pip install yt-dlp` ile otomatik kurulur (YouTube desteği için) |
| **İşletim Sistemi** | Windows 10+ | PowerShell 5.1+ gerekli (`run-local.ps1` / `.bat` scriptleri) |
| **İnternet** | ⚠️ Kısmen Gerekli | Çeviri API'leri bulut tabanlıdır (Supertonic TTS cihaz üzerinde %100 yerel çalışır) |

> [!NOTE]
> Tüm Python bağımlılıkları `run-local.bat` çalıştırıldığında otomatik kurulur. Manuel müdahale gerekmez.

---

## 🚀 Kurulum & Çalıştırma

### Hızlı Başlangıç (Tek Adım)

```bash
# 1. Projeyi klonlayın
git clone https://github.com/<kullanici>/youtube-turkce-ceviri.git
cd youtube-turkce-ceviri

# 2. Çalıştırın (venv + pip + bağımlılıklar otomatik kurulur)
run-local.bat
```

`run-local.bat` çalıştırıldığında:
1. ✅ Python 3.13 sanal ortamı (`.venv`) oluşturulur
2. ✅ `pip` kurulur (eksikse `get-pip.py` ile)
3. ✅ `requirements.txt` bağımlılıkları yüklenir
4. ✅ Port 8000 meşgulse otomatik boş port bulunur
5. ✅ Varsayılan tarayıcıda web paneli açılır
6. ✅ FastAPI sunucusu başlar → `http://127.0.0.1:8000/`

### Sunucuyu Yeniden Başlatma

```bash
# Port temizliği + sunucu yeniden başlatma
restart.bat
```

---

## 📁 Proje Yapısı

```
youtube-turkce-ceviri/
│
├── 📄 run-local.bat          # Ana başlatıcı (Windows — çift tıkla)
├── 📄 run-local.ps1          # PowerShell: venv oluşturma, pip, bağımlılık, sunucu başlatma
├── 📄 restart.bat             # Sunucuyu yeniden başlatma (port temizliği dahil)
├── 📄 restart.ps1             # Restart mantığı (port kill + run-local çağrısı)
├── 📄 free-yt-port.ps1        # Port yönetimi: meşgul portları temizleyen yardımcı fonksiyonlar
├── 📄 .gitignore              # Git tarafından yok sayılacak dosyalar
├── 📄 README.md               # Bu dosya
│
└── backend/                   # 🐍 Python FastAPI sunucusu
    ├── 📄 main.py             # Ana sunucu: FastAPI uygulaması, tüm API rotaları, iş kuyruğu
    ├── 📄 transcribe.py       # Whisper ile ses → metin (faster-whisper, int8, VAD filtresi)
    ├── 📄 translate.py        # Çeviri: LibreTranslate → Google (hızlı) → deep-translator
    ├── 📄 speak.py            # Supertonic TTS: metin → yerel Türkçe ses (ONNX)
    ├── 📄 video_pipeline.py   # Tam dublaj pipeline: ses çıkarma, parçalama, TTS, mux
    ├── 📄 jobs_store.py       # Bellek içi iş durumu (kuyruk, ilerleme takibi)
    ├── 📄 requirements.txt    # Python bağımlılıkları
    │
    └── web/
        └── 📄 index.html      # Web paneli (retro CRT temalı tek sayfa uygulama)
```

---

## 📂 Dosya Açıklamaları

### Kök Dizin — Başlatıcı Scriptler

| Dosya | Açıklama |
|-------|----------|
| `run-local.bat` | Windows için ana başlatıcı. Çift tıklayınca `run-local.ps1`'i PowerShell'de çalıştırır. |
| `run-local.ps1` | **Kurulum + sunucu başlatma.** Sanal ortam oluşturur, pip kurar, bağımlılıkları yükler, port kontrolü yapar, sunucuyu başlatır ve tarayıcıyı açar. Projenin kalbi. |
| `restart.bat` | Mevcut sunucuyu durdurup tekrar başlatır. Port meşgul kalmışsa temizleyerek yeniden başlar. |
| `restart.ps1` | `free-yt-port.ps1` ile port temizliği yapar, ardından `run-local.ps1`'i ayrı bir PowerShell sürecinde çalıştırır. |
| `free-yt-port.ps1` | Port yönetim fonksiyonları: `Clear-YtListenPort`, `Get-YtListeningPids`, `Stop-YtPortListener`, `Get-YtFirstFreeTcpPort`. Meşgul portları temizler veya otomatik boş port bulur. |

### Backend — Python Sunucusu

| Dosya | Açıklama |
|-------|----------|
| `main.py` | **FastAPI ana sunucu.** Tüm API endpointleri, CORS, iş kuyruğu yönetimi, dosya sunma (web paneli). Uvicorn ile `0.0.0.0:8000`'de çalışır. |
| `transcribe.py` | **Konuşma tanıma modülü.** `faster-whisper` ile WAV sesini metne çevirir. `small` modeli, int8 quantize, VAD filtresi ile sessiz kısımları atlar. `imageio-ffmpeg` ile ffmpeg'i otomatik PATH'e ekler. |
| `translate.py` | **Çeviri modülü.** Üç katmanlı strateji: (1) LibreTranslate (lokal — çalışıyorsa), (2) Google Translate hızlı API (ücretsiz), (3) `deep-translator` (yedek). |
| `speak.py` | **TTS (Text-to-Speech) modülü.** **Supertonic** ile cihaz üzerinde yüksek kaliteli (44.1kHz) ve çok hızlı yerel ses sentezi yapar. Bulut bağlantısına ihtiyaç duymaz, 31 dili (Türkçe dahil) destekler. |
| `video_pipeline.py` | **Tam dublaj pipeline.** Videodan ses çıkarma → WAV parçalara bölme → her parça için Whisper + çeviri + TTS → parçaları birleştirme → video ile mux'lama. `yt-dlp` ile YouTube indirme. |
| `jobs_store.py` | **İş durumu deposu.** Bellekte çalışan basit bir kuyruk. Her işin durumu (`queued`, `running`, `done`, `error`), ilerleme yüzdesi ve mesajı tutulur. Maksimum 24 iş, eski işler otomatik temizlenir. |
| `requirements.txt` | Python paket listesi. |

### Web Paneli

| Dosya | Açıklama |
|-------|----------|
| `frontend/index.html` | **Tek sayfalık web arayüzü.** Retro-futurist CRT sinema terminali teması. Video yükleme / YouTube bağlantısı girme, dublaj ayarları (ses, hız, parça süresi), ilerleme çubuğu ve sonuç indirme. Tüm CSS ve JS bu dosyanın içindedir. |

---

## 📦 Python Bağımlılıkları

| Paket | Açıklama |
|-------|----------|
| `fastapi` | Web framework — API sunucusu |
| `uvicorn[standard]` | ASGI sunucusu (FastAPI'yi çalıştırır) |
| `faster-whisper` | CTranslate2 tabanlı Whisper — hızlı konuşma tanıma |
| `imageio-ffmpeg` | ffmpeg binary'sini otomatik sağlar |
| `supertonic` | Yıldırım hızında, yerel, çok dilli cihaz üstü TTS motoru |
| `requests` | HTTP istekleri (çeviri API'leri için) |
| `python-multipart` | Dosya yükleme desteği (FastAPI) |
| `aiofiles` | Asenkron dosya işlemleri |
| `deep-translator` | Google Translate yedek çeviri kütüphanesi |
| `numpy` | Sayısal hesaplamalar (Whisper bağımlılığı) |
| `yt-dlp` | YouTube video indirici |

---

## 🌐 API Endpointleri

Sunucu çalışırken **Swagger dokümantasyonu** → `http://127.0.0.1:8000/docs`

| Metot | Endpoint | Açıklama |
|-------|----------|----------|
| `GET` | `/` | Web paneli arayüzü |
| `GET` | `/health` | Sağlık kontrolü |
| `GET` | `/api/info` | API bilgileri ve endpoint listesi |
| `POST` | `/process` | Tek ses parçası: ses → metin → çeviri → ses (eklenti modu) |
| `POST` | `/api/dub/start-url` | YouTube / URL'den tam dublaj başlat (JSON body) |
| `POST` | `/api/dub/start-upload` | Dosya yükleyerek tam dublaj başlat (multipart) |
| `POST` | `/api/jobs` | Eski yol: Request üzerinden iş oluştur |
| `GET` | `/api/jobs/{job_id}` | İş durumu sorgula (yüzde, mesaj, hata) |
| `GET` | `/api/jobs/{job_id}/download` | Tamamlanan dublajlı videoyu indir |
| `GET` | `/api/routes-debug` | Yüklü rotaları listele (404 ayıklama için) |
| `GET` | `/__yt_tr_ping` | Sunucu doğrulama (JSON yanıt dönmeli) |

---

## ⚙️ Ortam Değişkenleri

| Değişken | Varsayılan | Açıklama |
|----------|-----------|----------|
| `YT_TR_PORT` | `8000` | Sunucu dinleme portu |
| `YT_TR_LOG` | `info` | Uvicorn log seviyesi (`debug`, `info`, `warning`, `error`) |
| `YT_TR_RELOAD` | `off` | `1` yapılırsa kod değişince sunucu otomatik yeniden başlar (geliştirici modu) |
| `YT_TR_NO_PORT_KILL` | `off` | `1` yapılırsa meşgul port otomatik kapatılmaz |
| `YT_TR_NO_AUTO_PORT` | `off` | `1` yapılırsa port meşgulse otomatik alternatif aranmaz |
| `PYTHONUTF8` | `1` | Windows konsolda emoji/Unicode çıktı sorununu önler (script tarafından ayarlanır) |

---

## 🎯 Kullanım

### Web Paneli ile

1. `run-local.bat` çalıştırın
2. Tarayıcı otomatik açılır → `http://127.0.0.1:8000/`
3. **Dosya yükle** veya **YouTube bağlantısı** sekmesini seçin
4. Dublaj ayarlarını yapın (ses, hız, parça süresi)
5. **Başlat** butonuna tıklayın
6. İlerleme çubuğunu takip edin
7. Tamamlanınca videoyu izleyin veya indirin

### API ile (cURL)

```bash
# YouTube URL ile dublaj başlat
curl -X POST http://127.0.0.1:8000/api/dub/start-url \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://www.youtube.com/watch?v=XXXXX", "rate": "+40%", "voice": "tr"}'

# İş durumunu sorgula
curl http://127.0.0.1:8000/api/jobs/<job_id>

# Hazır videoyu indir
curl -o dublaj.mp4 http://127.0.0.1:8000/api/jobs/<job_id>/download
```

---

## 🛠️ Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| `Port 8000 dolu` | `restart.bat` kullanın veya `$env:YT_TR_PORT=8010` ile farklı port deneyin |
| `404 hatası` | Paneli **sadece** `http://127.0.0.1:<port>/` adresinden açın. Live Server veya `python -m http.server` **kullanmayın**. |
| `ffmpeg bulunamadı` | `imageio-ffmpeg` otomatik sağlar. Sorun devam ederse [ffmpeg.org](https://ffmpeg.org)'dan manuel kurun ve PATH'e ekleyin. |
| `yt-dlp hatası` | `pip install --upgrade yt-dlp` — YouTube sık format değiştirir |
| `Whisper yavaş` | Normal: ilk çalıştırmada model (~500 MB) indirilir. Sonraki çalıştırmalar hızlıdır. |

---

<p align="center">
  <strong>talhaeens</strong> · <a href="[https://talhaeens-ivy.netlify.app/](https://talhaeens-ivy.netlify.app/)">talhaeens-ivy.netlify.app</a>
</p>