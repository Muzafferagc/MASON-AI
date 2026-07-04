# Changelog / Değişiklik Günlüğü

Bu projedeki tüm önemli değişiklikler bu dosyada tutulur.
All notable changes to this project are documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/) · Sürümleme / Versioning: [SemVer](https://semver.org/)

> **Nasıl okunur:** En üstteki sürüm en yenidir. Her sürümde: **Eklendi** (yeni özellik),
> **Değişti** (mevcut davranış değişti), **Düzeltildi** (hata giderildi), **Kaldırıldı**.

---

## [Unreleased] — Yayınlanmadı

_Bir sonraki değişiklikler buraya eklenecek. Yeni bir sürüm hazır olduğunda tarih ve numara verilir._

---

## [2.0.0] — 2026-07-04

Büyük sürüm: sinematik V2 arayüz, çok daha akıllı ses sistemi ve GitHub'a hazırlık.
Major release: cinematic V2 UI, a much smarter voice system, and GitHub readiness.

### Eklendi / Added
- **Sinematik HUD arayüz (V2):** Sade, şık, filmvari tasarım; ortada sese göre parlayan MASON wordmark'ı, yüzen erişilebilir kontrol dock'u.
- **Renk paletleri / Themes:** Cyan, Altın/Amber, Neon Yeşil, Holografik Mor, Kızıl Alarm (⚙ Ayarlar → Görünüm Teması).
- **Barge-in:** Mason konuşurken "Hey Mason" dendiğinde sözünü kesip yeniden dinler (kendi sesini eko olarak ayırt eder).
- **Şifre korumalı hafıza silme:** `memory_password` ayarı doldurulursa hafıza silme işlemleri şifre ister.
- **Doğal Türkçe ses:** Varsayılan ses `tr-TR-AhmetNeural`, akıcı tempo (+22%).
- **Windows otomatik başlatma:** `kurulum.bat` / `kurulum.ps1`, masaüstü "MASON Aç/Kapat" simgeleri, `autostart.py`, `mason_kapat.py`.
- **GitHub hazırlığı:** `.gitignore` (API anahtarını korur), `config.example.json`, `GITHUB_REHBERI.md`, iki dilli `README.md` (kişisel "Neden bu projeyi geliştirdim? / Why I built this" bölümü dahil), bu `CHANGELOG.md`.

### Değişti / Changed
- Wake word dinleyici artık **kendini onaran** yapıda: mikrofon/stream çökse bile thread ölmüyor, yeniden başlıyor.
- Komut işleme (yavaş LLM çağrısı) artık **ayrı thread'de** çalışıyor; ses döngüsü bloke olmuyor.
- Her açılışta **temiz sohbet ekranı** (hafıza ve görevler korunur).
- Uygulama **gizli/arka planda** başlıyor ve "Hey Mason" bekliyor.

### Düzeltildi / Fixed
- "Hey Mason" ilk komuttan sonra bir daha algılamama sorunu (ses tamponu taşması dinleyiciyi öldürüyordu).
- Pencere her komutta küçülüp büyüyerek titreme sorunu (`restore()` çağrısı kaldırıldı).
- Sesi kapatıp açınca "Hey Mason"ın çalışmaması (UI artık `audio_ended` ile susturmayı anında temizliyor).
- Takılan bir LLM çağrısının wake'i kalıcı kilitlemesi (25 sn güvenlik zaman aşımı).
- "Hey Mason" deyince pencerenin tam ekrandan çıkıp pencereliye dönmesi.

### Biliniyor / Known issues
- **Ollama sağlayıcısı** henüz tam çalışmıyor; ileride ele alınacak.

---

## [1.0.0] — 2026-07-03

İlk çalışan sürüm — Faz 1'den Faz 3'e temel MASON.
First working version — core MASON from Phase 1 to Phase 3.

### Eklendi / Added
- **Faz 1:** Sohbet + kalıcı hafıza (SQLite, ağaç yapısı) + görev/plan motoru.
- **Faz 1.5:** Anlamsal hafıza araması (embeddings / RAG).
- **Faz 2:** Sesli konuşma — Whisper (ses→yazı) + edge-tts (yazı→ses).
- **Faz 3:** "Hey Mason" uyandırma + çift alkış + sistem tepsisi.
- Gemini (ücretsiz kota) ve Ollama sağlayıcı iskeleti; Jarvis temalı ilk arayüz.
