# Changelog / Değişiklik Günlüğü

Bu projedeki tüm önemli değişiklikler bu dosyada tutulur.
All notable changes to this project are documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/) · Sürümleme / Versioning: [SemVer](https://semver.org/)

> **Nasıl okunur:** En üstteki sürüm en yenidir. Her sürümde: **Eklendi** (yeni özellik),
> **Değişti** (mevcut davranış değişti), **Düzeltildi** (hata giderildi), **Kaldırıldı**.

---

## [Unreleased] — Yayınlanmadı

### Düzeltildi (kullanıcı geri bildirimleri)
- **"Hey Mason" deyince pencere öne gelmiyordu → (hotfix) sessiz çökme giderildi:** İlk denemede `_show_window`'a eklenen `window.on_top` toggle'ı, wake-dinleyici ARKA PLAN thread'inden çağrıldığı için Windows/EdgeChromium'da yakalanamayan bir native çökmeye (uygulama sessizce kapanıyordu) yol açtı. `on_top` kaldırıldı; öne getirme artık yalnızca thread-güvenli (GUI thread'ine marshal edilen) `show()` + `restore()` + `maximize()` + `evaluate_js(window.focus())` ile yapılıyor. Böylece "Hey Mason" deyince çökme sona erdi.
- **Ollama'da "sapıtma" / dediğini anlamama:** Asıl neden Ollama'nın varsayılan **bağlam penceresinin (num_ctx) 2048** olmasıydı — MASON'un uzun sistem promptu (hafıza + görevler + belgeler + kurallar) bunu aşınca promptun başı kesiliyor ve model talimatları göremiyordu. Artık `num_ctx: 8192` (ayarlanabilir) ve `temperature: 0.4` (talimata daha sadık). Bu, yerel modelle tutarlılığı belirgin artırır.
- **Ses tanıma kelimeleri iyi seçemiyordu:** Whisper artık `initial_prompt` (Türkçe + "Mason" bağlamı), `condition_on_previous_text=False` (kısa komutlarda halüsinasyonu önler), `beam_size=5`, `temperature=0` ve `no_speech_threshold` ile daha isabetli.
- **Silinen hafıza geri hatırlanıyordu:** Yeni **"forgotten" (mezar taşı) sistemi** — bir hafızayı sildiğinde içeriği kayda geçer; Mason sohbet geçmişinden onu **asla geri ekleyemez** (`remember` engellenir, id=0) ve sistem promptunda "bunları tekrar hatırlama" olarak işaretlenir. Yedekten geri yüklersen (import) bu işaret temizlenir ve bilgi geri gelir. Yani: sildiğin ve geri yüklemediğin bilgi gerçekten unutulur.

### Eklendi (kullanıcı istekleri)
- **Planları silme:** Planlar sekmesinde her planın yanında 🗑 butonu (hafıza/görev gibi; şifre koruması aktifse onay penceresinden geçer). Yeni `planner.delete_plan`, `apply_delete`'e `plan_ids` eklendi.
- **YEDEKLER sekmesi (save files):** Dock'ta yeni sekme; `yedekler/` klasöründeki tüm yedek dosyaları tarih, boyut ve kayıt sayısıyla listelenir. Her yedekte **↺ GERİ YÜKLE** ve 🗑 sil butonu (`api.list_backups` / `restore_backup` / `delete_backup`).
- **"Kendini kapat" → uyku modu:** Sesli veya yazılı "kendini kapat / uyku moduna geç / gizlen / arka plana geç / ekrandan git" dediğinde Mason kısa bir onay verip **X'e basılmış gibi pencereyi gizler** ve tepside "Hey Mason" demeni beklemeye devam eder (tamamen kapanmaz).

### Eklendi (Faz 4 — Dosya yükleme + Belge hafızası / RAG)
- **Her türden dosya yükleme (ChatGPT/Gemini gibi):** Dock'a 📎 butonu ve tüm ekranı kaplayan **sürükle-bırak** katmanı eklendi. Desteklenen türler: PDF, Word (.docx), Excel (.xlsx/.csv), metin & kod (.txt/.md/.py/.js…), **görsel** (.png/.jpg…) ve **ses** (.mp3/.wav…). Desteklenmeyen tür/eksik kütüphane sessizce atlanır, uygulama asla çökmez.
- **İçerik çıkarma:** PDF → `pypdf`, Word → `python-docx`, Excel → `openpyxl`, metin/kod/CSV → doğrudan (kodlama tahminiyle), **görsel → Gemini "görü" (vision/OCR)**, **ses → faster-whisper** (Faz 2 altyapısı). Hiçbiri için zorunlu kurulum yok; kurulu olmayan tür için bilgilendirici mesaj döner.
- **Optimum veri toplama (RAG):** Her belge anlamlı **parçalara** bölünür (~1200 karakter, üst üste binen), her parçaya **embedding** çıkarılır. Soru sorduğunda 100 sayfalık bir PDF'in tamamı değil, soruyla anlamca **en ilgili 5-8 parça** prompt'a girer (`documents.format_for_prompt`) — hem hızlı hem Gemini kotası dostu. Kaynak dosya adı yanıt bağlamında belirtilir.
- **BELGELER paneli:** Dock'ta yeni sekme; yüklü belgeler tür ikonu, boyut, parça sayısı, tarih ve önizleme ile listelenir. Her belgede 🗑 silme butonu (şifre koruması aktifse onay penceresinden geçer; belge + parçaları birlikte silinir).
- **Belgeler kalıcıdır:** Sohbet kapansa da hafızada kalır; Mason belgeden kalıcı bir bilgi/hedef öğrenirse proaktif olarak `remember` ile kaydeder.
- **Yeni:** `mason/documents.py` modülü; `documents` + `doc_chunks` DB tabloları; `api.upload_files` (yerel dosya seçici), `api.upload_blob` (sürükle-bırak base64 yedeği), `api.delete_document`, `api.list_documents`. Yüklenen dosyalar `belgeler/` klasörüne kopyalanır (gitignore'da). requirements.txt'e `pypdf`, `python-docx`, `openpyxl` eklendi.
- **Testler:** `tests/test_core.py`'ye 28 belge testi eklendi (tür tespiti, parçalama, ingest, retrieval, silme, hatalı dosyada çökmeme) — tümü geçti.

### Düzeltildi (silme güvenliği)
- **"Fitness'ı sil" deyince TÜM hafıza siliniyordu:** Sistem promptuna sert SİLME KURALLARI eklendi — `clear_memory` yalnızca kullanıcı açıkça "tüm hafızayı sil" derse kullanılabilir; belirli bir konu için ilgili `#id`'lerle `forget` zorunlu. (Küçük yerel modeller bu kuralı ihlal etmeye meyilliydi.)
- **Görev silme şifre onayından geçmiyordu:** `delete_task` ve yeni `clear_tasks` aksiyonları da artık şifre korumasına dahil — onay penceresi açılır, şifre doğruysa siler. Onay penceresi artık NE silineceğini de yazar ("Silinecek: 2 hafıza + 1 görev").

### Eklendi (silme & şifre)
- **Manuel silme:** Hafıza ve Görevler sekmelerinde her kaydın yanında 🗑 butonu. Şifre varsa onay penceresi açılır; yoksa direkt siler (`api.apply_delete`).
- **Şifre çift kontrol (double-check):** Ayarlar'da şifre ilk kez belirlenirken "yeni + tekrar" iki alana aynı şifre yazılmak zorunda; değiştirirken "eski + yeni + yeni tekrar" istenir; kaldırmak için eski şifre gerekir (`api.change_password`). Şifre artık arayüze hiç gönderilmez (`has_memory_password` bayrağı gider), ayarlar ekranında görünmez.

### Eklendi (Ollama fazı)
- **Ollama sağlayıcısı tam çalışır durumda:**
  - Ayarlar'da **⚡ OLLAMA'YI TEST ET** butonu: sunucu ayakta mı, sohbet modeli (`ollama_model`) ve hafıza modeli (`ollama_embedding_model`) yüklü mü — tek tıkla kontrol. Yüklü modeller model kutusuna öneri olarak dolar (`api.ollama_status`).
  - Ayarlar'daki motor seçimine **Hybrid** seçeneği eklendi (önerilen); hybrid'de hem Gemini hem Ollama alanları görünür.
  - Model yüklü değilse artık anlaşılır hata: `'llama3.2' modeli yüklü değil → ollama pull llama3.2`. Bağlantı yoksa ollama.com kurulum yönlendirmesi.
  - Düşünen modellerin (deepseek-r1 vb.) `<think>...</think>` iç monoloğu cevaptan temizleniyor.
  - `keep_alive: 10m` — model bellekte kalır, ardışık sorular çok daha hızlı.
  - Eski Ollama sürümleri için embedding geri düşüşü: `/api/embed` yoksa `/api/embeddings` denenir.
  - **`ollama_kontrol.bat`**: çift tıkla Ollama kurulum/çalışma/model durumunu gösteren teşhis aracı.
  - 10 yeni birim testi (sahte HTTP ile; gerçek Ollama gerektirmez).

### Değişti
- **API kota sorununa karşı "hybrid" LLM modu:** `provider` artık `hybrid` olabilir. Önce Gemini kullanılır; kota/limit hatası (HTTP 429/503) gelince otomatik olarak yerel Ollama'ya düşer ve `hybrid_cooldown_sec` (varsayılan 900 sn) boyunca doğrudan yerel modeli kullanır — böylece uygulama kota dolunca artık çökmüyor. Embedding'ler de aynı sırayı (Gemini→Ollama) izler.


### Kaldırıldı
- **`GITHUB_REHBERI.md` git deposundan çıkarıldı:** Kişisel kurulum rehberi artık GitHub'da paylaşılmıyor; yerelde tutuluyor ve tüm commit geçmişinden temizlendi. `.gitignore`'a eklendi.

### Düzeltildi
- **Hafıza silme çalışmıyordu:** "hafızayı sil" dendiğinde MASON sadece "onay bekliyorum" diyor ama hiçbir şey silmiyordu. LLM bir silme aksiyonu üretmediği için `pending_forget` boş kalıyor, şifre penceresi hiç açılmıyordu. Artık tüm hafızayı silmek için `clear_memory` aksiyonu var; şifre penceresi açılıp doğru şifre girilince silme gerçekleşiyor.

### Eklendi
- `clear_memory` aksiyonu ve `memory.forget_all()` / `memory.all_memory_ids()` yardımcıları — tüm hafızayı şifre korumalı akıştan geçirerek toplu silme.
- Sistem promptu güncellendi: silme talebinde LLM artık `forget`/`clear_memory` aksiyonunu üretmek ZORUNDA; şifreyi uygulama sorar, kullanıcıdan sohbete şifre yazması istenmez.
- **Hafıza yedekleme:** `memory.export_memories()` / `import_memories()` + Ayarlar'da Dışa Aktar / İçe Aktar butonları. Hafıza `yedekler/` klasörüne tarihli JSON olarak yazılır; en yeni yedekten geri yüklenir (aynı içerik atlanır).
- **Hatırlatıcılar:** `mason/reminders.py` (yaklaşan/geciken görev mantığı) + arka planda periyodik kontrol; sistem tepsisi bildirimi ve arayüz uyarısı.
- **MIT LICENSE** ve **GitHub Actions CI** (her push'ta `tests/test_core.py`, Python 3.10–3.12).
- Yedekleme ve hatırlatıcılar için birim testleri; commit düzeni Conventional Commits'e geçirildi (README'de belgelendi).

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
- ~~**Ollama sağlayıcısı** henüz tam çalışmıyor; ileride ele alınacak.~~ *(Unreleased sürümünde tamamlandı.)*

---

## [1.0.0] — 2026-07-03

İlk çalışan sürüm — Faz 1'den Faz 3'e temel MASON.
First working version — core MASON from Phase 1 to Phase 3.

### Eklendi / Added
- **Faz 1:** Sohbet + kalıcı hafıza (SQLite, ağaç yapısı) + görev/plan motoru.
- **Faz 1.5:** Anlamsal hafıza araması (embeddings / RAG).
- **Faz 2:** Sesli 