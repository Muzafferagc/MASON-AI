# Changelog / Değişiklik Günlüğü

Bu projedeki tüm önemli değişiklikler bu dosyada tutulur.
All notable changes to this project are documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/) · Sürümleme / Versioning: [SemVer](https://semver.org/)

> **Nasıl okunur:** En üstteki sürüm en yenidir. Her sürümde: **Eklendi** (yeni özellik),
> **Değişti** (mevcut davranış değişti), **Düzeltildi** (hata giderildi), **Kaldırıldı**.

---

## [Unreleased] — Yayınlanmadı

### Eklendi (Takvim daha fonksiyonel — Apple Takvim gibi)
- **Güne tıkla → gün detayı:** Takvimde herhangi bir güne tıklayınca o günün tüm görev/hatırlatıcıları açılır; her birini oradan **tamamlayabilir, düzenleyebilir veya silebilirsin** (tekrar edenler 🔁 ile).
- **Kendin ekle:** Gün penceresindeki **"+ Bu güne görev / hatırlatıcı ekle"** ile doğrudan o güne yeni bir şey koyabilirsin (başlık, öncelik, tekrar, not). Ayrıca GÖREVLER sekmesinin üstünde **"+ Yeni Görev / Hatırlatıcı"** butonu — artık her şeyi Mason'a söylemek zorunda değilsin.
- Takvim hücreleri tıklanabilir/vurgulu hale geldi; yeni `api.add_task_ui` ve detay modalında "oluştur" modu (tarih önceden dolu gelir).

### Düzeltildi (KRİTİK — görev ekleme sessizce bozuktu)
- **`agent.py` tekrar (recurrence) için `planner.add_task`'ı 6 argümanla çağırıyordu ama `planner.py` hâlâ 5 argüman kabul ediyordu** → her `add_task` çağrısı `TypeError` fırlatıp sessizce yutuluyordu, yani sohbetten görev ekleme çalışmıyordu. `planner.py` tamamlandı; artık `recurrence` parametresi ve tamamlanınca sonraki tekrarı oluşturan `complete_task` var. Eski veritabanlarına `tasks.recurrence` ve `memories.note` sütunları güvenli göç ile eklendi.

### Eklendi (Faz 8 — Apple tarzı yineleme, doğallık, detay paneli)
- **Tekrar eden hatırlatıcılar (Apple Reminders gibi):** "her gün / her hafta / her ayın 8'inde / her yıl" dediğinde görev yinelenir olarak kaydedilir (recurrence). Tamamlanınca (kutucuğu işaretleyince) otomatik olarak **sonraki tarih** için yeni görev oluşur. Ay sonları akıllıca kırpılır (31 Ocak +1 ay → 28 Şubat). Takvimde tekrar günlerinin hepsi 🔁 ile gösterilir; görev listesinde de 🔁 rozeti.
- **Detay / düzenleme paneli:** Hafıza, görev veya plana **tıklayınca** (planlarda ✏️) detay penceresi açılır; başlık, proje, öncelik, tarih, tekrar, durum, kategori ve **serbest not/açıklama** düzenlenebilir. Hafızaya kullanıcı notu alanı eklendi (📝 ile işaretlenir).
- **Konumumu algıla:** Ayarlar'da 📍 buton, IP'den bulunduğun gerçek şehri + koordinatı otomatik doldurur (ücretsiz, anahtarsız). Artık hava/konum için Antalya varsayılanına takılı kalmazsın.

### Düzeltildi (doğallık & gerçekçilik — sistem promptu)
- **Boş/uydurma görev & plan:** Model bazen boş başlıklı görev/plan üretip kaydediyordu → `execute_actions` artık boş içerikli remember/add_task/save_plan'ı **reddediyor**; prompt da "istenmeden görev/plan oluşturma, boş şey kaydetme" diye netleştirildi.
- **"Kaydet" derken silme şifresi çıkması:** Küçük model kaydet isteğinde yanlışlıkla silme aksiyonu üretiyordu → silme aksiyonları artık **yalnızca kullanıcı mesajında gerçek silme niyeti** ("sil/unut/kaldır/temizle") varsa uygulanıyor.
- **Bilmediği konumu iddia etme:** Prompta "GPS'in/canlı konumun yok; hafızada yazmıyorsa şehir/hava iddia etme, bilmiyorsan söyle" kuralı eklendi.
- **Doğal Türkçe + kalıcı hafıza:** Prompt daha sıcak/doğal konuşacak, kimlik/şehir/tercih gibi kalıcı bilgileri proaktif olarak hafızaya kaydedecek (böylece diğer sohbetlerde de seni bilir) şekilde yeniden yazıldı. Robotik/çeviri kokan ifadeler ("Hangi görevde oluyorum" gibi) engellendi.

### Not (Ollama mantık hataları)
- Küçük yerel model (`llama3.2` 3B) Türkçede ve talimat takibinde zayıftır; yukarıdaki doğrulama + prompt iyileştirmeleri en kötü davranışları engeller ama en tutarlı sonuç için **Gemini** ya da daha büyük yerel model (`qwen2.5:7b`+) önerilir.

### Düzeltildi (KRİTİK — "no such column: conversation_id")
- **Mevcut veritabanında her mesaj/yeni sohbet hata veriyordu:** Sohbet geçmişi için eklenen `CREATE INDEX ... ON messages(conversation_id)` satırı SCHEMA içindeydi ve `executescript` sırasında **migrasyon sütunu eklemeden ÖNCE** çalışıyordu. Eski `mason.db`'de `messages` tablosu var ama `conversation_id` sütunu henüz olmadığından index oluşturma her `get_conn` çağrısında çöküyor, migrasyon hiç çalışamıyor, sütun hiç eklenemiyordu → mesaj gönderme, yeni sohbet, hafıza, görev dahil DB'ye dokunan her şey "no such column: conversation_id" veriyordu. **Çözüm:** index artık SCHEMA'dan çıkarıldı; `_migrate()` içinde, sütun kesin eklendikten sonra oluşturuluyor (ayrıca `commit()` ile Python 3.12+/3.14 sqlite davranışına karşı kesinleştirildi). Eski veritabanı sorunsuz göç ediyor; eski mesajlar "Önceki sohbet" olarak korunuyor.

### Düzeltildi (dayanıklılık — sesli komut takılması)
- **Ollama'da sesli komut "İŞLİYORUM"da takılıp kalıyordu:** İki kök neden vardı. (1) Birçok arka plan thread'i (sohbet + hatırlatıcı + brifing + embedding) aynı anda veritabanına eriştiğinde SQLite "database is locked" hatası verip sesli komut yolunu çökertiyordu → artık **WAL modu + busy_timeout** ile eşzamanlı erişim güvenli. (2) Sesli komut yolunda (`_on_command`) hata yakalama yoktu; bir istisna olunca arayüz kilitleniyordu → artık `agent.chat` **asla istisna fırlatmıyor** (her durumda anlaşılır bir yanıt/hatayla dönüyor) ve `_on_command` her durumda `voiceReply` çağırıp arayüzü serbest bırakıyor. Kısacası Ollama yavaş/hatalı olsa bile ekran artık takılmıyor.

### Eklendi
- **Belirgin "+ YENİ SOHBET" butonu:** GEÇMİŞ sekmesinin en üstünde büyük bir buton; ayrıca dock'taki "⌦ YENİ" ile aynı işi yapar (mevcut sohbeti geçmişte bırakıp yeni sohbet başlatır).
- **Brifing tetikleme penceresi:** Sabah brifingi artık yalnızca hedef saatten sonraki ~2 saatlik pencerede tetiklenir; uygulamayı gece geç açınca yanlışlıkla brifing patlamaz.

### Eklendi (Faz 7 — Çok-sohbetli konuşma geçmişi / ChatGPT-Gemini gibi)
- **Sohbetler artık kaydediliyor ve saklanıyor:** Her sohbet ayrı bir kayıt (conversation). Dock'ta yeni **GEÇMİŞ** sekmesi: tüm sohbetlerin başlık, mesaj sayısı ve tarihiyle listelenir; birine tıklayınca o sohbet ekrana yüklenir ve kaldığın yerden devam edersin. Aktif sohbet vurgulanır. Başlık ilk mesajından otomatik üretilir.
- **Açılışta artık geçmiş SİLİNMİYOR:** Eskiden her açılışta sohbet temizleniyordu. Artık temiz ekranla başlar ama önceki tüm sohbetler GEÇMİŞ'te durur. "⌦ YENİ" butonu mevcut sohbeti geçmişte bırakıp yeni bir sohbet başlatır.
- **Her sohbetin bağlamı ayrı:** LLM'e yalnızca aktif sohbetin mesajları verilir; sohbetler birbirine karışmaz.
- **Sohbet silme:** GEÇMİŞ'te her sohbetin yanında 🗑 (şifre koruması aktifse onay penceresinden geçer; "Silinecek: … + N sohbet").
- **Sohbet yedekleme:** Ayarlar'da "SOHBETLERİ YEDEKLE / GERİ YÜKLE"; yedekler `yedekler/` klasörüne yazılır ve YEDEKLER sekmesinde 💬 Sohbet olarak (🧠 Hafıza yedeklerinden ayrı) görünür, oradan da geri yüklenip silinebilir.
- **Yeni:** `mason/chats.py`, `conversations` tablosu + `messages.conversation_id` (eski veritabanları otomatik göç eder — eski mesajlar "Önceki sohbet"e taşınır). `api.list_chats/load_chat/delete_chat/rename_chat/export_chats/import_chats`. 32 yeni test (sohbet + göç) — hepsi geçti.

### Eklendi (Faz 6 — Kesintisiz konuşma, takvim, bildirim, brifing)
- **Kesintisiz konuşma modu:** Ayardan açılır. Mason cevabını bitirince (ses bittiğinde) ~8 sn boyunca "Hey Mason" demeden dinlemeye devam eder; konuşursan yeni komut olarak işler, sessizlikte normal wake-word moduna döner. Mevcut "komut penceresi" mekanizması yeniden açılarak yapıldı (`WakeWordListener.open_command_window`, `audio_ended` kancası).
- **TAKVİM sekmesi:** Dock'ta yeni sekme; aylık ızgara, görevler son tarihine göre günlere yerleşir (öncelik renkli nokta ile), bugün vurgulanır, ‹ › ile ay gezinme. Tamamen yerel.
- **.ics dışa aktarma:** Takvimdeki ⤓ .ICS butonu, son tarihli görevleri standart iCalendar (.ics) dosyası olarak `disari_aktar/` klasörüne yazar → Google/Outlook/Apple takvimine aktarabilirsin (`mason/ics_export.py`, `api.export_ics`).
- **Bildirim entegrasyonu:** Bildirimler artık 3 kanaldan gider — Windows yerel toast (plyer varsa), sistem tepsisi balonu ve arayüz içi bildirim. Ayardan `notify_native` ile açılıp kapanır.
- **Sabah brifingi + hava durumu:** Ayardan belirlediğin saatte (varsayılan 08:00) günde bir kez "günün brifingi": selam + tarih + hava durumu + bugünkü/gecikmiş görevler. İstersen sesli de okunur; sohbete de eklenir. Hava durumu **Open-Meteo** ile (ücretsiz, API anahtarı gerekmez; enlem/boylam ayarlanır, varsayılan Antalya). `mason/weather.py`, `mason/briefing.py`, `_briefing_loop`, "🌅 Brifingi şimdi dene" butonu.
- **Yeni ayarlar:** kesintisiz mod, Windows bildirimi, sabah brifingi (aç/saat/sesli), hava durumu (aç/şehir/enlem/boylam). requirements.txt'e opsiyonel `plyer` eklendi. 21 yeni test (hava/brifing/ics/kesintisiz) — hepsi geçti.

### Düzeltildi
- **Yedek silme çalışmıyordu:** Silme şifresi ayarlıyken YEDEKLER sekmesindeki 🗑 boş şifreyle çağırdığı için sunucu reddediyordu. Artık diğer silmeler gibi şifre onay penceresinden geçiyor (yedek de "Silinecek: … + N yedek" özetinde görünür).

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