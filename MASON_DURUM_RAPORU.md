# MASON AI — Proje Durum Raporu

**Tarih:** 2026-07-08
**Amaç:** Bu rapor, projeyi başka AI modellerine (ChatGPT, Gemini, vb.) göstererek yeni fikir/geliştirme önerisi almak için hazırlandı. Aşağıdaki her şey mevcut kod tabanının gerçek durumunu yansıtır.

---

## 1. Proje Nedir

**MASON** — Iron Man'deki Jarvis'ten ilham alan, Muzaffer'in (Akdeniz Üniversitesi, Yapay Zeka ve Veri Mühendisliği, 2026-2027'de 2. sınıf) kişisel olarak geliştirdiği, **tamamen ücretsiz** çalışan bir masaüstü yapay zeka asistanı. Temel farkı: konuştukça öğrendiği bilgileri **kalıcı hafızaya** kaydeder ve unutmaz (ChatGPT/Gemini sohbetlerinin aksine).

- **Platform:** Windows masaüstü uygulaması (pywebview ile native pencere)
- **Dil:** Python (backend) + HTML/CSS/Vanilla JS (arayüz) — framework yok
- **Bütçe:** 0 TL — Gemini API ücretsiz kota + opsiyonel yerel Ollama
- **Dil desteği:** Türkçe ağırlıklı (kullanıcının konuştuğu dilde cevap verir)
- **Lisans:** MIT, GitHub'da açık kaynak (repo: `Muzafferagc/MASON-AI`), CI (GitHub Actions) her push'ta testleri koşuyor

---

## 2. Mimari

```
Chat UI (HTML/JS, sinematik HUD) ⇄ pywebview köprüsü ⇄ Python Agent
                                                          │
                        ┌─────────────┬─────────────┬────┴────┬──────────┐
                        ▼             ▼             ▼         ▼          ▼
                    SQLite DB    Planlayıcı    LLM katmanı  Belgeler   Ses (STT/TTS)
                   (hafıza/     (görev/plan)   (Gemini/     (RAG)     (Whisper/
                    sohbet)                     Ollama/                edge-tts)
                                                 Hybrid)
```

### Aksiyon protokolü (projenin çekirdek tasarımı)
1. Kullanıcı mesajı gelince `agent.py`, kalıcı hafızayı + açık görevleri + tarihi + (varsa) belge alıntılarını tek bir sistem promptuna gömer.
2. LLM normal bir cevap yazar; gerekirse cevabın içine görünmez bir ` ```json:actions``` ` bloğu ekler (hafızaya kaydet, görev aç, plan kaydet, hafıza/görev sil…).
3. MASON bu bloğu ayıklar, çalıştırır, kullanıcıya göstermeden doğal cevabı ekrana/hoparlöre verir.

Bu, sağlayıcıdan bağımsız (Gemini/Ollama farketmez) basit ama güçlü bir "tool calling" mekanizması.

### LLM sağlayıcı stratejisi
- **provider: hybrid** (varsayılan) — önce Gemini dener; kota/limit hatası (429/503) gelirse otomatik Ollama'ya düşer, `hybrid_cooldown_sec` (900 sn) boyunca yerelde kalır.
- **Gemini:** `gemini-2.5-flash` (sohbet), `gemini-embedding-001` (anlamsal arama)
- **Ollama:** `llama3.2` (sohbet, şu an zayıf), `nomic-embed-text` (embedding, İngilizce ağırlıklı)

---

## 3. Dosya Yapısı ve Boyutlar

```
run.py               1025 satır  — uygulama girişi, pywebview köprüsü, tepsi, tek-örnek kilidi
mason/agent.py         349 satır  — beyin: prompt + aksiyon protokolü + kesintisiz-mod bitiş algısı
mason/documents.py     399 satır  — dosya yükleme + RAG (PDF/Word/Excel/görsel/ses)
mason/wakeword.py      268 satır  — "Hey Mason" algılama + barge-in
mason/memory.py        251 satır  — kalıcı hafıza (ağaç yapısı + embedding arama)
mason/planner.py       188 satır  — görev/plan motoru + tekrar (recurrence)
mason/llm.py           184 satır  — Gemini/Ollama/Hybrid sağlayıcı arayüzü
mason/chats.py         174 satır  — çok-sohbetli konuşma geçmişi
mason/database.py      167 satır  — SQLite şema + migrasyonlar
mason/voice.py         163 satır  — mikrofon + Whisper STT + edge-tts
mason/weather.py       105 satır  — Open-Meteo hava durumu
mason/briefing.py       84 satır  — sabah brifingi
mason/embeddings.py     84 satır  — anlamsal arama altyapısı
mason/ics_export.py     77 satır  — takvim .ics dışa aktarma
autostart.py            74 satır  — Windows açılışa ekleme
mason/config.py         72 satır  — ayarlar (config.json)
mason/reminders.py      68 satır  — yaklaşan/geciken görev hatırlatıcı
mason_kapat.py           28 satır — uygulamayı kapatma
────────────────────────────────
Toplam backend:       ~3760 satır Python
ui/index.html          (sinematik HUD, tek dosya HTML/CSS/JS)
tests/test_core.py      473 satır — 134 doğrulama (check) noktası, hepsi geçiyor
```

**SQLite tabloları:** `memories`, `tasks`, `conversations`, `messages`, `plans`, `documents`, `doc_chunks`, `forgotten` (silinen hafızalar için "mezar taşı" tablosu).

---

## 4. Tamamlanan Özellikler (kronolojik)

| Faz | Durum | Özet |
|---|---|---|
| Faz 1 | ✅ | Sohbet + kalıcı hafıza (SQLite, ağaç yapısı) + görev/plan motoru |
| Faz 1.5 | ✅ | Anlamsal hafıza araması (embeddings/RAG, cosine similarity) |
| Faz 2 | ✅ | Sesli konuşma — Whisper (STT) + edge-tts (TTS, `tr-TR-AhmetNeural`, +22% hız) |
| Faz 3 | ✅ | "Hey Mason" wake word + Windows açılışta arka planda çalışma (tepsi ikonu) |
| V2 | ✅ | Sinematik HUD arayüz (sese göre parlayan wordmark), 5 renk teması, barge-in (konuşurken kesip dinleme) |
| V2.1 | ✅ | Hafıza yedekleme (JSON dışa/içe aktarma) + görev hatırlatıcıları + CI |
| Ollama fazı | ✅ | Hybrid mod, uygulama içi test butonu, teşhis aracı (`ollama_kontrol.bat`), anlaşılır hata mesajları |
| Faz 4 (RAG) | ✅ | Dosya yükleme (PDF/Word/Excel/metin/görsel/ses), parçalama + embedding, ilgili parça seçimi |
| Silme güvenliği | ✅ | Şifre korumalı silme, "mezar taşı" (forgotten) sistemi, spesifik silme kuralları (LLM'in yanlışlıkla her şeyi silmesini engelleme) |
| Faz 6 | ✅ | Kesintisiz konuşma modu (8 sn pencere), Takvim sekmesi, .ics dışa aktarma, Windows toast bildirimleri, sabah brifingi + hava durumu (Open-Meteo) |
| Faz 7 | ✅ | Çok-sohbetli konuşma geçmişi (ChatGPT/Gemini tarzı) — sohbet listesi, geçiş, silme, yedekleme |
| Faz 8 | ✅ | Apple-tarzı tekrarlayan hatırlatıcılar (recurrence), detay/düzenleme paneli, IP'den otomatik konum algılama |
| Takvim v2 | ✅ (en son commit) | Güne tıkla → gün detayı, doğrudan o güne görev/hatırlatıcı ekleme |

**Son commit'ler (`git log`):**
```
ca6285c feat: takvim fonksiyonel — güne tıkla, gün detayı, kendin ekle
5c65f6f fix+feat: recurrence tamamlandı, doğal prompt, konum, detay paneli
84ce2bd fix(KRİTİK): no such column: conversation_id — migrate fix
ccd6e2d fix: sesli komut takılması (DB WAL + agent/voice dayanıklılık)
d6312bd feat: çok-sohbetli konuşma geçmişi
511dfaf feat: kesintisiz konuşma, takvim+.ics, bildirim, brifing+hava
```

---

## 5. Şu Anki Çalışma (henüz commit edilmemiş)

`mason/agent.py` üzerinde **kesintisiz sesli mod için "konuşma bitişi algılama"** özelliği geliştiriliyor (henüz commit edilmedi, working directory'de değişiklik olarak duruyor):

- **LLM sinyali:** Kullanıcı sohbeti belirgin şekilde bitirdiğinde LLM cevabının sonuna görünmez bir `⟦END⟧`/`[BITTI]`/`<DONE>` işareti koyar; uygulama bunu ayıklayıp mikrofonu tekrar açmaz, normal "Hey Mason" beklemesine döner.
- **Yerel yedek (LLM'siz):** "yok bir şey", "sağ ol", "tamam", "iyi geceler" gibi kısa kapanış ifadelerini regex/kelime listesiyle yakalayan `is_closing_phrase()` fonksiyonu — LLM çağrısı beklemeden anında karar verir. Komut içeren mesajları ("tamam şunu ekle") yanlışlıkla bitiş saymamak için 5 kelimeden uzun mesajları ve komut kelimelerini eledi.
- Aynı diff içinde `agent.py`'de küçük bir refactor de var (eski genel `except Exception` bloğu kaldırılmış, `_chat` iç fonksiyonuna ayrıştırma yapılmış — bu kısmın testlerle doğrulanması gerekiyor).

Bu değişiklik henüz test edilip commit'lenmedi — bir sonraki adım bunu bitirip commit atmak.

---

## 6. Bilinen Sorunlar / Kısıtlamalar

1. **Yerel model (Ollama `llama3.2` 3B) Türkçede zayıf:** Bozuk cümleler kuruyor ("thingsini", "confirmasiyona needsin" gibi karışık kelimeler), silme kurallarını ihlal etmeye meyilli. Prompt sıkılaştırmalarıyla en kötü davranışlar engellendi ama tutarlı sonuç için Gemini veya daha büyük yerel model gerekiyor.
2. **Embedding modeli İngilizce ağırlıklı:** `nomic-embed-text` Türkçe anlamsal aramada ideal değil; `bge-m3` daha iyi olurdu ama henüz entegre edilmedi (ayarlara embedding model seçim alanı da eklenmedi — şu an sadece `config.json`'dan elle değiştiriliyor).
3. **Ollama modellerinin kurulu olup olmadığı doğrulanmadı:** `ollama pull llama3.2` ve `ollama pull nomic-embed-text` yapıldı mı henüz teyit edilmemiş (kullanıcının donanımı RTX 4070 12GB + 64GB RAM — çok daha büyük modelleri rahat kaldırır: `qwen3:14b` önerilen, `gemma3:12b`, `qwen3:8b` alternatifler).
4. **Takvim entegrasyonu yerel:** Google Calendar gibi dış takvimlerle iki yönlü senkron yok, sadece tek yönlü `.ics` dışa aktarma var.
5. **Dosya/bilgisayar kontrolü yok:** README'deki "Faz 4 — Genişleme" vizyonunda listelenen "Mason, projemi aç" gibi bilgisayar kontrolü özellikleri henüz yapılmadı.
6. **Pomodoro / alışkanlık takibi / uzun vadeli ilerleme raporları yok.**
7. **Tek platform:** Sadece Windows için kurulum betikleri var (kurulum.bat/.ps1, autostart.py Windows'a özel).

---

## 7. Bekleyen Kişisel Hatırlatmalar (proje sahibinin notları)

1. **Proje tamamen bitince** MASON'un plan listesine "AI ile ses/görüntü üretimi (audio/image generation)" eklenecek — bilerek şimdi eklenmedi.
2. **Yerel model yükseltmesi:** `qwen3:14b` (ana öneri, Türkçesi iyi ve aksiyon formatına disiplinli), `gemma3:12b`, `qwen3:8b` (hız öncelikliyse) — donanım rahat kaldırır.
3. **Türkçe embedding:** `bge-m3` kurulup ayarlara "embedding modeli" alanı eklenmesi gerekiyor.
4. Ollama modellerinin gerçekten indirilip indirilmediğinin kontrolü.

---

## 8. Test Durumu

- `tests/test_core.py`: **134 doğrulama noktası**, tamamı sahte (mock) LLM sağlayıcı ile — gerçek API/Ollama gerektirmez.
- GitHub Actions CI: her push'ta Python 3.10–3.12'de otomatik çalışıyor.
- Kapsanan alanlar: hafıza (kayıt/silme/ağaç/format), planlayıcı (görev/tekrar), sohbet geçmişi + migrasyon, belge yükleme/RAG, hava durumu/brifing/ics/kesintisiz mod, Ollama sağlayıcı (sahte HTTP).

---

## 9. Teknoloji Yığını Özeti

| Katman | Araç | Neden |
|---|---|---|
| Masaüstü kabuk | pywebview | Native pencere + Python↔JS köprüsü |
| Arayüz | HTML/CSS/Vanilla JS | Bağımlılıksız, sinematik Jarvis HUD |
| Veritabanı | SQLite | Yerel, kalıcı, sıfır kurulum |
| LLM | Gemini API (ücretsiz) / Ollama (yerel) / Hybrid | Ücretsizlik + kota dayanıklılığı |
| Anlamsal arama | Gemini/Ollama embedding + cosine similarity | RAG, hafıza büyüyünce ilgili kayıt seçimi |
| STT | faster-whisper | Yerel, ücretsiz, Türkçe destekli |
| TTS | edge-tts | Ücretsiz, doğal Türkçe ses |
| Wake word | faster-whisper (tiny) + enerji analizi | Ekstra kurulum gerektirmeden "Hey Mason" |
| Tepsi/otomatik başlatma | pystray + Pillow | Arka plan çalışma, Windows entegrasyonu |
| Bildirim | plyer (opsiyonel) + tepsi + arayüz | 3 kanaldan bildirim |
| Belge okuma | pypdf, python-docx, openpyxl | RAG için içerik çıkarma |

---

## 10. Diğer AI'lara Sorulacak Açık Sorular / Fikir İstenecek Alanlar

Bu rapor başka bir AI'ya götürülürken özellikle şu alanlarda fikir istenebilir:

- Yerel model (Ollama) performansını Gemini seviyesine yaklaştırma stratejileri (prompt mühendisliği, few-shot örnekler, daha küçük ama görev-odaklı fine-tune?)
- Türkçe RAG/embedding kalitesini artırma (bge-m3 entegrasyonu dışında başka yaklaşımlar var mı?)
- "Kesintisiz sesli mod bitiş algılama" için LLM+kural hibrit yaklaşımının sağlamlaştırılması (şu an test edilmemiş taslak halinde)
- Bilgisayar kontrolü / dosya sistemi entegrasyonu için güvenli bir tasarım (yetkilendirme, sandbox, komut onayı)
- Google Calendar gibi dış servislerle iki yönlü senkron için ücretsiz kalarak nasıl entegrasyon yapılabilir
- Pomodoro / alışkanlık takibi / uzun vadeli hedef raporlama için hafıza şemasının nasıl genişletilebileceği
- Çoklu platform desteği (macOS/Linux) için pywebview + autostart mekanizmasının taşınabilirliği

---

*Bu rapor, projenin `AI Planning and Schedule for MASON AI` klasöründeki gerçek kod, git geçmişi, README, CHANGELOG, ROADMAP ve kişisel hatırlatma dosyaları taranarak 2026-07-08 tarihinde hazırlanmıştır.*
