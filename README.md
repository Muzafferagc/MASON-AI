<div align="center">

# 🤖 MASON

**Jarvis benzeri, hiçbir şeyi unutmayan kişisel yapay zeka asistanı**
*A Jarvis-like personal AI assistant that never forgets anything*

Kalıcı hafıza · Planlama · Sesli konuşma · "Hey Mason" · Sinematik HUD arayüz
Persistent memory · Planning · Voice chat · "Hey Mason" wake word · Cinematic HUD

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)
![LLM](https://img.shields.io/badge/LLM-Gemini%20%7C%20Ollama-8E75FF)
![Status](https://img.shields.io/badge/Sürüm-V2-3ce7ff)

**[🇹🇷 Türkçe](#-türkçe)** · **[🇬🇧 English](#-english)**

</div>

---

## 🇹🇷 Türkçe

MASON, Iron Man'deki Jarvis'ten ilham alan, tamamen **ücretsiz** çalışabilen kişisel bir yapay zeka asistanıdır. En büyük farkı: seninle konuştukça projelerini, hedeflerini ve planlarını **kalıcı hafızasına** kaydeder ve asla unutmaz. Sesle konuşabilir, "Hey Mason" diyerek her an çağrılabilir ve sinematik bir HUD arayüzüne sahiptir.

### 💡 Neden bu projeyi geliştirdim?

> Bu projeyi yapay zeka desteğiyle geliştirdim. Ama asıl amacım bir uygulama yazmaktan çok; zamanımı, planlarımı ve projelerimi **istikrarlı ve doğru** bir şekilde yönetebilmek. MASON, hem bu projeyi hem de bundan sonraki projelerimi ve planlarımı daha sağlam kurgulamam için bir temel.
>
> Bu yeni çağda, yapay zeka desteği olmadan geliştirilen projelerin giderek zorlanacağına inanıyorum; ama her şeyin uçtan uca yapay zeka tarafından yapılmasının da doğru olmadığını düşünüyorum. Bu yüzden yapay zekayı bir **araç** olarak kullanıp yönü, kararları ve öğrenmeyi kendimde tutmayı seçtim. Amacım ilk adımlarımı bile sağlam atmak — çünkü sağlam atılan ilk adımlar, sonraki her şeyi taşır.

### ✨ Özellikler

- **Kalıcı hafıza** — Projelerini, hedeflerini, sınav tarihlerini, tercihlerini hatırlar; bilgileri projelere göre "ağaç" gibi bağlar.
- **Anlamsal arama (RAG)** — Hafıza büyüdükçe, sorunla anlamca en ilgili bilgileri seçer.
- **Planlama & görevler** — Görev ekler, önceliklendirir, günlük/haftalık/aylık plan çıkarır.
- **Sesli konuşma** — Mikrofonla konuş (Whisper ile yazıya çevirir), Mason doğal bir Türkçe sesle (Ahmet) cevap verir.
- **"Hey Mason" uyandırma** — Arka planda dinler; adını duyunca öne gelir. Konuşurken bile "Hey Mason" dersen susup seni dinler (barge-in).
- **Sinematik HUD arayüz** — Sade, şık, filmvari tasarım; sese göre parlayan MASON wordmark'ı ve seçilebilir renk paletleri.
- **Şifre korumalı hafıza silme** — İstersen hafıza silme işlemleri şifre ister.
- **Ücretsiz** — Gemini API ücretsiz kotası ya da tamamen yerel Ollama.

### 🧰 Teknoloji

Python · [pywebview](https://pywebview.flowrl.com/) (masaüstü pencere) · SQLite · Google Gemini / Ollama · [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (ses→yazı) · [edge-tts](https://github.com/rany2/edge-tts) (yazı→ses) · HTML/CSS/JS (Jarvis HUD)

### 🚀 Kurulum (Windows)

1. **Python kur** (varsa atla): [python.org/downloads](https://www.python.org/downloads/) → kurulumda **"Add Python to PATH"** kutusunu işaretle.
2. **Depoyu indir:**
   ```bash
   git clone https://github.com/KULLANICI-ADIN/mason-ai.git
   cd mason-ai
   ```
3. **Paketleri kur:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Ayar dosyanı oluştur:** `config.example.json` dosyasını `config.json` olarak kopyala.
5. **Ücretsiz Gemini anahtarı al:** [aistudio.google.com](https://aistudio.google.com) → "Get API key" → kopyala. (İlk açılışta ayarlar penceresine de yapıştırabilirsin.)
6. **Çalıştır:**
   ```bash
   python run.py
   ```

### 🎙️ Kullanım

- **Yazarak:** Alttaki kutuya komutunu yaz, Gönder.
- **Sesle:** 🎤 butonuna tıkla, konuş, bitince tekrar tıkla.
- **"Hey Mason":** Uygulama açıkken (pencere gizli olsa bile) adını söyle. Sadece "Hey Mason" → "Efendim?" der; "Hey Mason, bugün ne yapmalıyım?" gibi tek nefeste de sorabilirsin. **Konuşurken "Hey Mason" dersen sözünü kesip seni dinler.**
- **Temalar:** ⚙ Ayarlar → Görünüm Teması (Cyan / Altın / Yeşil / Mor / Kızıl).
- **Hafıza şifresi:** ⚙ Ayarlar → Hafıza Silme Şifresi. Doldurursan silme işlemi şifre ister.

**Örnek komutlar:**
> *"Önümüzdeki hafta vize haftam, pazartesi matematik sınavım var"* → hafızaya kaydeder, görev açar
> *"Bu haftayı planlar mısın?"* → önceliklere göre haftalık plan yapar
> *"Bugün ne yapmalıyım?"* → görev ve hafızana bakarak önerir

### 🖥️ Windows açılışında otomatik başlatma

`kurulum.bat` dosyasına bir kez çift tıkla. Bu; masaüstüne **MASON Aç** / **MASON Kapat** simgeleri ekler, açılışa ekler ve Mason'u arka planda başlatır. (Detay: `autostart.py`)

### 🧩 Alternatif: Ollama (internet/anahtar gerektirmez)

> ⚠️ **Not:** Ollama sağlayıcısı şu an geliştirme aşamasında; ilerideki bir sürümde tam desteklenecek. Şimdilik Gemini önerilir.

### 📂 Proje yapısı

```
run.py               → uygulamayı başlatır (pencere + JS köprüsü, tek örnek, tepsi)
kurulum.bat / .ps1   → masaüstü simgeleri + otomatik başlatma kurulumu
autostart.py         → Windows açılışına ekleme/çıkarma
mason_kapat.py       → Mason'u tamamen kapatır
mason/config.py      → ayarlar (config.json)
mason/database.py    → SQLite tabloları
mason/memory.py      → kalıcı hafıza (ağaç yapısı)
mason/planner.py     → görev ve plan motoru
mason/llm.py         → Gemini / Ollama sağlayıcıları
mason/embeddings.py  → anlamsal hafıza araması
mason/voice.py       → mikrofon + Whisper + sesli yanıt
mason/wakeword.py    → "Hey Mason" algılama + barge-in
mason/agent.py       → Mason'un beyni: prompt + aksiyon protokolü
ui/index.html        → sinematik HUD arayüz (V2)
tests/test_core.py   → testler
```
> Verilerin `mason.db` dosyasında saklanır — **bu dosyayı silme!**

### 🔧 Sorun giderme

| Sorun | Çözüm |
|------|-------|
| `pip tanınmıyor` | Python'u "Add to PATH" işaretli yeniden kur |
| Gemini 400/403 | API anahtarını kontrol et |
| Gemini 404 | Ayarlardan model adını güncelle |
| Gemini 429 | Günlük ücretsiz kota doldu; yarın sıfırlanır |
| Pencere açılmıyor | `pip install pywebview --upgrade` |
| "Hey Mason" tepkisiz | Net konuş; ilk algılama model yüklemesiyle ~10 sn gecikebilir |
| Mikrofon çalışmıyor | Windows → Gizlilik → Mikrofon izinleri |

### 🗺️ Yol haritası

- [x] Faz 1: Chat + kalıcı hafıza + planlama
- [x] Faz 1.5: Anlamsal hafıza araması (embeddings)
- [x] Faz 2: Sesli konuşma (Whisper + TTS)
- [x] Faz 3: "Hey Mason" + otomatik başlatma
- [x] V2: Sinematik HUD, barge-in, temalar, şifreli hafıza
- [ ] Ollama sağlayıcısını tam çalışır hale getirme
- [ ] Kesintisiz konuşma modu, hatırlatıcılar/bildirimler

---

## 🇬🇧 English

MASON is a **free**, Jarvis-inspired personal AI assistant. Its superpower: as you talk to it, it saves your projects, goals and plans to a **persistent memory** and never forgets. It talks with you by voice, can be summoned anytime by saying "Hey Mason", and features a cinematic HUD interface.

### 💡 Why I built this

> I built this project with the help of AI. But my real goal isn't just to ship an app — it's to manage my time, plans and projects in a **consistent and reliable** way. MASON is a foundation that helps me structure both this project and my future projects and plans more soundly.
>
> I believe that in this new era, projects built with no AI assistance will increasingly struggle — yet I also don't think everything should be built end-to-end by AI. So I chose to use AI as a **tool**, while keeping the direction, the decisions and the learning on my side. My aim is to make even my first steps solid — because first steps taken well carry everything that follows.

### ✨ Features

- **Persistent memory** — Remembers your projects, goals, exam dates and preferences; links facts into a project "tree".
- **Semantic search (RAG)** — As memory grows, it picks the facts most relevant to your question.
- **Planning & tasks** — Adds tasks, prioritizes, generates daily/weekly/monthly plans.
- **Voice chat** — Speak via microphone (Whisper transcribes); Mason replies in a natural voice.
- **"Hey Mason" wake word** — Listens in the background and comes forward when called. You can even interrupt it mid-sentence by saying "Hey Mason" (barge-in).
- **Cinematic HUD** — Minimal, sleek, movie-like design; a MASON wordmark that glows with your voice, plus selectable color palettes.
- **Password-protected memory wipe** — Optionally require a password before any memory is deleted.
- **Free** — Google Gemini free tier or fully local Ollama.

### 🧰 Tech stack

Python · [pywebview](https://pywebview.flowrl.com/) · SQLite · Google Gemini / Ollama · [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (STT) · [edge-tts](https://github.com/rany2/edge-tts) (TTS) · HTML/CSS/JS (Jarvis HUD)

### 🚀 Setup (Windows)

1. **Install Python** (skip if present): [python.org/downloads](https://www.python.org/downloads/) → check **"Add Python to PATH"**.
2. **Clone the repo:**
   ```bash
   git clone https://github.com/YOUR-USERNAME/mason-ai.git
   cd mason-ai
   ```
3. **Install packages:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Create your config:** copy `config.example.json` to `config.json`.
5. **Get a free Gemini key:** [aistudio.google.com](https://aistudio.google.com) → "Get API key". (You can also paste it into the in-app settings on first launch.)
6. **Run:**
   ```bash
   python run.py
   ```

### 🎙️ Usage

- **Type:** enter a command in the bottom box and Send.
- **Voice:** click 🎤, speak, click again to finish.
- **"Hey Mason":** while the app runs (even hidden), say its name. Just "Hey Mason" → it says "Yes?"; or ask in one breath: "Hey Mason, what should I do today?". **Say "Hey Mason" while it's speaking to interrupt and be heard.**
- **Themes:** ⚙ Settings → Appearance Theme (Cyan / Gold / Green / Violet / Crimson).
- **Memory password:** ⚙ Settings → Memory-Delete Password. If set, deletions require the password.

### 🖥️ Auto-start on Windows boot

Double-click `kurulum.bat` once. It adds **MASON Aç** / **MASON Kapat** desktop icons, registers auto-start, and launches Mason in the background. (See `autostart.py`.)

### 🧩 Alternative: Ollama (no internet/key needed)

> ⚠️ **Note:** The Ollama provider is currently a work in progress and will be fully supported in a future release. Gemini is recommended for now.

### 📂 Project structure

See the Turkish section above — same files. Your data lives in `mason.db` — **don't delete it!**

### 🗺️ Roadmap

- [x] Phase 1: Chat + persistent memory + planning
- [x] Phase 1.5: Semantic memory search (embeddings)
- [x] Phase 2: Voice chat (Whisper + TTS)
- [x] Phase 3: "Hey Mason" + auto-start
- [x] V2: Cinematic HUD, barge-in, themes, password-protected memory
- [ ] Make the Ollama provider fully working
- [ ] Continuous conversation mode, reminders/notifications

---

<div align="center">

Made with 💙 by **Muzaffer** · Akdeniz University, AI & Data Engineering
Değişiklik geçmişi için / For change history: **[CHANGELOG.md](CHANGELOG.md)**

</div>
