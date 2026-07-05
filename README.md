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
![Tests](https://github.com/Muzafferagc/MASON-AI/actions/workflows/tests.yml/badge.svg)
![License](https://img.shields.io/badge/License-MIT-green)

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
- **Şifre korumalı hafıza silme** — İstersen hafıza silme işlemleri şifre ister; onay penceresi açılır.
- **Hafıza yedekleme** — Tüm hafızanı tek tıkla JSON olarak dışa aktar, gerektiğinde geri yükle (aynı bilgiler atlanır).
- **Hatırlatıcılar** — Görevlerin son tarihi geldiğinde/geçtiğinde arka planda seni uyarır (sistem tepsisi + arayüz bildirimi).
- **Ücretsiz** — Gemini API ücretsiz kotası ya da tamamen yerel Ollama.

### 🧰 Teknoloji

Saf Python + web arayüz; ağır bir çatı (framework) yok. Her parça, kurulmazsa uygulamayı çökertmeyecek şekilde *opsiyonel* tutuldu.

| Katman | Kullanılan | Ne işe yarıyor |
|--------|-----------|----------------|
| Masaüstü kabuk | [pywebview](https://pywebview.flowrl.com/) | HTML arayüzünü native pencerede gösterir, Python↔JS köprüsü kurar |
| Arayüz | HTML + CSS + Vanilla JS | Sinematik Jarvis HUD; kütüphane bağımlılığı yok |
| Veri | SQLite (`sqlite3`) | Hafıza, görev, plan ve sohbet kalıcı olarak yerelde tutulur |
| Beyin (LLM) | Google Gemini / [Ollama](https://ollama.com) | Cevap üretir; sağlayıcı-bağımsız arayüz (`llm.py`) |
| Anlamsal arama | Gemini/Ollama embedding + kosinüs benzerliği | Hafıza büyüyünce en ilgili bilgileri seçer (RAG) |
| Kulak (STT) | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) + [sounddevice](https://python-sounddevice.readthedocs.io/) | Mikrofonu dinler, konuşmayı yazıya çevirir (yerel/ücretsiz) |
| Ağız (TTS) | [edge-tts](https://github.com/rany2/edge-tts) | Cevabı doğal Türkçe sesle okur |
| Uyandırma | faster-whisper (tiny) + enerji/tepe analizi | "Hey Mason" ve çift alkış algılama, barge-in |
| Tepsi & otomatik başlatma | [pystray](https://github.com/moses-palmer/pystray) + [Pillow](https://python-pillow.org/) | Arka planda çalışma, bildirimler, Windows açılışına ekleme |

### 🧠 Nasıl çalışıyor? (mimari)

MASON'ın kalbi basit ama güçlü bir **aksiyon protokolü**dür — sağlayıcıdan bağımsız bir "tool calling":

1. Mesajın gelince `agent.py`, kalıcı hafızanı, açık görevlerini ve tarihi tek bir sistem promptuna gömer.
2. LLM normal bir cevap yazar; gerekiyorsa cevabın içine gizli bir <code>```json:actions```</code> bloğu ekler (hafızaya kaydet, görev aç, plan kaydet, hafıza sil…).
3. Mason bu bloğu ayıklayıp çalıştırır, kullanıcıya göstermez; kalan doğal cevabı ekrana/hoparlöre verir.

Öne çıkan tasarım kararları:

- **Hafıza ağacı** — Her bilgi bir kategori (`project/goal/preference/fact`) ve bir projeyle saklanır; ilgili bilgiler aynı "dala" bağlanır.
- **RAG / anlamsal arama** — Hafıza 40 kaydı geçince, sorunun embedding'i ile en yakın anlamlı kayıtlar seçilir; embedding alınamazsa sessizce en yeni kayıtlara döner (asla çökmez).
- **Barge-in** — Mason konuşurken "Hey Mason" dersen, kendi sesinin ekosunu ayırt edip sözünü keser ve seni dinler.
- **Şifre korumalı silme** — Silme talebi doğrudan yürütülmez; onay penceresi açılır, doğru şifre girilince `apply_forget` çalışır.
- **Dayanıklılık** — Ses/tepsi paketleri opsiyoneldir; kurulmazsa ilgili özellik kapanır, uygulama yine açılır.

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

1. [ollama.com](https://ollama.com) adresinden indir ve kur.
2. Terminalde modelleri indir: `ollama pull llama3.2` ve `ollama pull nomic-embed-text` (anlamsal hafıza için).
3. MASON Ayarlar → motor olarak **Ollama** ya da **Hybrid** seç → **⚡ OLLAMA'YI TEST ET** ile doğrula.

Kurulumu kontrol etmek için `ollama_kontrol.bat` dosyasına çift tıklayabilirsin. **Hybrid** mod önerilir: önce Gemini, kota dolunca otomatik yerel Ollama.

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
mason/reminders.py   → yaklaşan/geciken görev hatırlatıcı mantığı
mason/agent.py       → Mason'un beyni: prompt + aksiyon protokolü
ui/index.html        → sinematik HUD arayüz (V2)
tests/test_core.py   → testler
yedekler/            → hafıza yedekleri (JSON) — dışa aktarınca oluşur
.github/workflows/   → her push'ta testleri çalıştıran CI
```
> Verilerin `mason.db` dosyasında saklanır — **bu dosyayı silme!** Güvenlik için ⚙ Ayarlar → Hafıza Yedekleme'den ara ara yedek al.

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
- [x] V2.1: Hafıza yedekleme (JSON) + görev hatırlatıcıları + CI
- [x] Ollama sağlayıcısını tam çalışır hale getirme (hybrid mod, uygulama içi test, teşhis aracı)
- [ ] Kesintisiz konuşma modu, takvim/bildirim entegrasyonu

### 🧑‍💻 Geliştirme & katkı

Testleri çalıştır: `python tests/test_core.py` (her push'ta CI de çalıştırır).

**Commit mesajı düzeni — [Conventional Commits](https://www.conventionalcommits.org/):** Her mesaj kısa bir önekle başlar ve *sadece o commit'te değişeni* anlatır (baştan her şeyi tekrar yazma):

```
fix:      hata düzeltmesi        →  fix: hafıza silme onay akışı
feat:     yeni özellik           →  feat: hafıza yedekleme (JSON dışa/içe aktarma)
docs:     sadece dokümantasyon   →  docs: README teknoloji tablosu
refactor: davranış değişmeden kod düzeni
test:     test ekleme/düzeltme
chore:    yapılandırma, CI, bağımlılık
```

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
- **Password-protected memory wipe** — Optionally require a password before any memory is deleted; a confirmation dialog appears.
- **Memory backup** — Export your whole memory to JSON in one click and restore it later (duplicates are skipped).
- **Reminders** — Warns you in the background when tasks are due or overdue (system-tray + in-app notification).
- **Free** — Google Gemini free tier or fully local Ollama.

### 🧰 Tech stack

Pure Python + a web UI, no heavy framework. Every part is *optional* — if a package isn't installed, that feature turns off instead of crashing the app.

Python · [pywebview](https://pywebview.flowrl.com/) (native window + Python↔JS bridge) · SQLite (persistent memory/tasks/plans) · Google Gemini / [Ollama](https://ollama.com) (provider-agnostic LLM) · embeddings + cosine similarity (semantic RAG search) · [faster-whisper](https://github.com/SYSTRAN/faster-whisper) + [sounddevice](https://python-sounddevice.readthedocs.io/) (STT) · [edge-tts](https://github.com/rany2/edge-tts) (TTS) · [pystray](https://github.com/moses-palmer/pystray) + [Pillow](https://python-pillow.org/) (tray, notifications, auto-start) · HTML/CSS/vanilla JS (Jarvis HUD)

**How it works:** `agent.py` embeds your memory, open tasks and the date into one system prompt; the LLM replies normally and may include a hidden <code>```json:actions```</code> block (remember, add task, save plan, delete memory…). MASON strips and runs that block, then shows the natural reply. Memory is a category/project "tree"; once it grows past 40 items, semantic search picks the most relevant facts (falling back to newest if embeddings are unavailable — it never crashes).

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

1. Install from [ollama.com](https://ollama.com).
2. Pull the models: `ollama pull llama3.2` and `ollama pull nomic-embed-text` (for semantic memory).
3. In MASON Settings pick **Ollama** or **Hybrid** and verify with the **⚡ TEST OLLAMA** button.

**Hybrid** is recommended: Gemini first, automatic local fallback when the quota runs out. `ollama_kontrol.bat` is a double-click diagnostic tool.

### 📂 Project structure

See the Turkish section above — same files. Your data lives in `mason.db` — **don't delete it!**

### 🗺️ Roadmap

- [x] Phase 1: Chat + persistent memory + planning
- [x] Phase 1.5: Semantic memory search (embeddings)
- [x] Phase 2: Voice chat (Whisper + TTS)
- [x] Phase 3: "Hey Mason" + auto-start
- [x] V2: Cinematic HUD, barge-in, themes, password-protected memory
- [x] V2.1: Memory backup (JSON) + task reminders + CI
- [x] Make the Ollama provider fully working (hybrid mode, in-app test, diagnostics)
- [ ] Continuous conversation mode, calendar/notification integration

### 🧑‍💻 Development

Run tests: `python tests/test_core.py` (CI runs them on every push). Commits follow [Conventional Commits](https://www.conventionalcommits.org/) — a short prefix (`fix:`, `feat:`, `docs:`, `refactor:`, `test:`, `chore:`) describing only what changed in that commit.

---

<div align="center">

Made with 💙 by **Muzaffer** · Akdeniz University, AI & Data Engineering
Değişiklik geçmişi için / For change history: **[CHANGELOG.md](CHANGELOG.md)**

</div>
