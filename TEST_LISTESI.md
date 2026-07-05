# MASON — Kapsamlı Test Listesi

Bu liste, MASON'un tüm özelliklerini elle test etmen için hazırlandı. Her maddeyi
yaptıkça kutucuğu işaretle. **Beklenen** satırı, olması gereken sonucu söyler.
Bir madde beklendiği gibi çalışmazsa not al, birlikte düzeltelim.

> İpucu: İlk kez test ediyorsan **0. Ön Hazırlık** ve **15. Otomatik Testler**
> bölümleriyle başla; sonra sırayla ilerle.

---

## 0. Ön Hazırlık (bir kez)

- [ ] Terminalde proje klasöründe: `pip install -r requirements.txt`
      **Beklenen:** pypdf, python-docx, openpyxl, plyer dahil hepsi kurulur.
- [ ] `config.json` içinde Gemini API anahtarın var mı kontrol et (Ayarlar'dan da girilebilir).
- [ ] Ollama'yı test edeceksen: `ollama_kontrol.bat` çift tıkla **veya** terminalde
      `ollama pull llama3.2` ve `ollama pull nomic-embed-text` (daha iyi Türkçe için `ollama pull qwen2.5:7b`).
- [ ] Uygulamayı başlat: `python run.py` (ilk açılışta hata görmek istersen konsollu çalıştır).
      **Beklenen:** Boot animasyonu → MASON ekranı → "Sistemler devrede, Muzaffer" karşılaması.

---

## 1. Temel Sohbet

- [ ] "Merhaba, kendini tanıt" yaz, Gönder.
      **Beklenen:** Mason birkaç saniyede Türkçe, doğal bir yanıt verir.
- [ ] Ayarlar → Motor: **Gemini** seçiliyken birkaç mesaj at.
      **Beklenen:** Hızlı ve akıcı yanıtlar.
- [ ] Ayarlar → Motor: **Ollama** (veya Hybrid) seçip kaydet, sonra mesaj at.
      **Beklenen:** İlk yanıt biraz yavaş olabilir (model belleğe yükleniyor) ama gelir; ekran **takılıp kalmaz**.
- [ ] Uzun bir soru sor (birkaç cümle).
      **Beklenen:** Yanıt kesilmeden gelir (Ollama'da bağlam artık kesilmiyor).

---

## 2. Hafıza (Mason'un seni hatırlaması)

- [ ] "Ben Akdeniz Üniversitesi'nde yapay zeka mühendisliği okuyorum" de.
      **Beklenen:** HAFIZA sekmesinde bu bilgi görünür (sağ üstteki HAFIZA sayacı artar).
- [ ] "En sevdiğim dil Python" de, sonra HAFIZA sekmesine bak.
      **Beklenen:** Yeni bilgi proje/konu altında ağaç gibi gruplanmış görünür.
- [ ] HAFIZA sekmesinde bir bilginin yanındaki 🗑'a bas (şifren varsa şifre iste).
      **Beklenen:** Şifre doğruysa bilgi silinir.
- [ ] **Tombstone testi:** Bir hafızayı sil, sonra Mason'a o konuyu sor.
      **Beklenen:** Mason silinen bilgiyi **geri hatırlamaz** ve tekrar kaydetmez.
- [ ] Sildiğin bilgiyi geri istiyorsan: Ayarlar → İÇE AKTAR (hafıza yedeğinden).
      **Beklenen:** Bilgi geri gelir (silme işareti temizlenir).

---

## 3. Görevler

- [ ] "Yarın matematik final çalışmam lazım, görev ekle" de.
      **Beklenen:** GÖREVLER sekmesinde görev, öncelik ve tarihle görünür.
- [ ] "Bu hafta yapılacakları önceliklendir" de.
      **Beklenen:** Mason görevleri sıralar; gerekiyorsa plan önerir.
- [ ] Bir görevin kutucuğunu işaretle (tamamla).
      **Beklenen:** Görev "tamamlandı" görünümüne geçer.
- [ ] Bir görevin yanındaki 🗑'a bas.
      **Beklenen:** Şifre varsa onay ister, sonra siler.

---

## 4. Planlar

- [ ] "Bana haftalık bir çalışma planı yap" de.
      **Beklenen:** Sohbette markdown plan çıkar; PLANLAR sekmesinde kaydedilir.
- [ ] PLANLAR sekmesinde plan başlığına tıkla.
      **Beklenen:** Plan açılıp kapanır (detay görünür).
- [ ] Bir planın yanındaki 🗑'a bas.
      **Beklenen:** Şifre varsa onay ister, sonra siler.

---

## 5. Takvim + .ics

- [ ] Birkaç göreve son tarih ver (farklı günlere).
- [ ] TAKVİM sekmesini aç.
      **Beklenen:** Aylık ızgara; görevler günlerinde, öncelik renkli nokta ile; bugün vurgulu.
- [ ] ‹ › oklarıyla ay değiştir.
      **Beklenen:** Önceki/sonraki aya geçer.
- [ ] **⤓ .ICS** butonuna bas.
      **Beklenen:** "N görev dışa aktarıldı → disari_aktar/…" mesajı; `disari_aktar/` klasöründe .ics dosyası oluşur.
- [ ] O .ics dosyasını Google/Outlook Takvim'e aktarmayı dene.
      **Beklenen:** Görevler takvimde tüm-gün etkinlik olarak görünür.

---

## 6. Belge Yükleme (RAG)

- [ ] Dock'taki 📎 ile bir **PDF** yükle.
      **Beklenen:** "işlendi (N parça)" bildirimi; BELGELER sekmesinde belge görünür.
- [ ] Yüklediğin belge hakkında soru sor ("bu belgede X ne diyor?").
      **Beklenen:** Mason belgeden alıntılayarak yanıtlar, kaynak dosya adını belirtir.
- [ ] Bir **Word (.docx)** ve bir **Excel/CSV** yükle.
      **Beklenen:** İçerikleri okunur, sorulara yanıt verir.
- [ ] Bir **metin/kod** dosyası yükle (.txt/.py).
      **Beklenen:** İçerik işlenir.
- [ ] Bir **görsel** yükle (Gemini anahtarı gerekli).
      **Beklenen:** Görselin içeriği/yazısı okunur (OCR).
- [ ] Bir **ses** dosyası yükle (.mp3/.wav).
      **Beklenen:** Konuşma yazıya çevrilip işlenir (biraz sürebilir).
- [ ] Dosyayı pencereye **sürükle-bırak**.
      **Beklenen:** Bırakma katmanı çıkar, dosya işlenir.
- [ ] BELGELER'de bir belgenin 🗑'ına bas.
      **Beklenen:** Belge ve parçaları silinir.

---

## 7. Sohbet Geçmişi (GEÇMİŞ)

- [ ] Birkaç mesaj at, sonra dock'ta **⌦ YENİ**'ye bas.
      **Beklenen:** Ekran temizlenir, "Yeni sohbet başladı" mesajı gelir.
- [ ] GEÇMİŞ sekmesini aç.
      **Beklenen:** Önceki sohbet başlık + mesaj sayısı + tarihle listelenir.
- [ ] GEÇMİŞ'in üstündeki **+ YENİ SOHBET** butonunu dene.
      **Beklenen:** Yeni boş sohbet başlar.
- [ ] Listeden eski bir sohbete tıkla.
      **Beklenen:** O sohbet ekrana yüklenir, kaldığın yerden devam edebilirsin (aktif sohbet vurgulanır).
- [ ] Bir sohbetin 🗑'ına bas.
      **Beklenen:** Şifre varsa onay ister, sonra siler.
- [ ] Uygulamayı kapatıp yeniden aç.
      **Beklenen:** Ekran temiz başlar **ama** önceki sohbetler GEÇMİŞ'te durur (silinmez).

---

## 8. Yedekleme (Hafıza + Sohbet)

- [ ] Ayarlar → **DIŞA AKTAR (YEDEKLE)** (hafıza).
      **Beklenen:** "N hafıza yedeklendi → yedekler/…".
- [ ] Ayarlar → **SOHBETLERİ YEDEKLE**.
      **Beklenen:** "N sohbet yedeklendi → yedekler/…".
- [ ] YEDEKLER sekmesini aç.
      **Beklenen:** Yedekler listelenir; 🧠 Hafıza ve 💬 Sohbet olarak ayrı ayrı işaretli.
- [ ] Bir yedekte **↺ GERİ YÜKLE**'ye bas.
      **Beklenen:** İçerik geri yüklenir.
- [ ] Bir yedeğin 🗑'ına bas (şifren varsa onay ister).
      **Beklenen:** Yedek dosyası silinir. *(Bu daha önce çalışmıyordu — artık çalışmalı.)*

---

## 9. Ses & "Hey Mason"

- [ ] Sohbet kutusundaki 🎤'ye bas, konuş, tekrar bas.
      **Beklenen:** Konuşman yazıya çevrilir ve gönderilir.
- [ ] Sesli yanıt açıkken (🔊) bir soru sor.
      **Beklenen:** Mason cevabı sesli okur.
- [ ] Uygulama açıkken/tepsideyken **"Hey Mason"** de.
      **Beklenen:** Pencere öne gelir *(artık çökmüyor)*, "Efendim?" der.
- [ ] "Hey Mason, bugün ne yapmalıyım?" de (tek cümlede komut).
      **Beklenen:** Uyanır ve komutu işler.
- [ ] Çift alkışla uyanmayı dene (ayar açıksa).
      **Beklenen:** İki alkışta uyanır.
- [ ] Mason konuşurken **"Hey Mason"** de (barge-in).
      **Beklenen:** Konuşmayı keser, seni dinlemeye geçer.

---

## 10. Kesintisiz Konuşma Modu

- [ ] Ayarlar → **Kesintisiz konuşma modu**'nu aç, kaydet.
- [ ] "Hey Mason" ile uyandır, bir soru sor, cevabı bekle, sonra **"Hey Mason" DEMEDEN** yeni bir şey söyle.
      **Beklenen:** Cevap bitince ~8 sn dinlemeye devam eder; yeni sözünü komut olarak işler.
- [ ] Cevaptan sonra sus.
      **Beklenen:** ~8 sn sonra normal "Hey Mason" moduna döner.

---

## 11. Uyku Modu

- [ ] "Kendini kapat" **veya** "uyku moduna geç" de (yazılı ya da sesli).
      **Beklenen:** Kısa onay verir ("Uyku moduna geçiyorum…"), sonra pencere gizlenir (X'e basılmış gibi), tepside dinlemeye devam eder.
- [ ] Sonra "Hey Mason" ile geri çağır.
      **Beklenen:** Pencere geri gelir.

---

## 12. Bildirimler + Sabah Brifingi + Hava

- [ ] Ayarlar → **Windows yerel bildirimleri** açık; **Her sabah brifing** aç; şehir/enlem/boylam gir; saat ayarla; kaydet.
- [ ] Ayarlar → **🌅 Brifingi şimdi dene**'ye bas.
      **Beklenen:** Bildirim çıkar; brifing sohbete eklenir (selam + tarih + hava + görevler); ayar açıksa sesli okunur.
- [ ] Hava durumu satırını kontrol et.
      **Beklenen:** Şehir + sıcaklık + durum + en düşük/yüksek (Open-Meteo, anahtarsız). İnternet yoksa hava satırı atlanır, gerisi gelir.
- [ ] Bir gecikmiş/bugünkü görev varken hatırlatıcı bildirimini bekle (30 dk'da bir kontrol).
      **Beklenen:** Bildirim gelir.

---

## 13. Ayarlar & Görünüm

- [ ] Tema değiştir (cyan/gold/green/violet/crimson), kaydet.
      **Beklenen:** Arayüz rengi/parıltısı değişir.
- [ ] İsmini değiştir, kaydet.
      **Beklenen:** Mason yeni isimle hitap eder.
- [ ] Silme şifresi **belirle** (yeni + tekrar), sonra bir şey silmeyi dene.
      **Beklenen:** Onay penceresi şifre ister.
- [ ] Şifreyi **değiştir** (eski + yeni + tekrar) ve **kaldır** (eski).
      **Beklenen:** Her işlem doğru çalışır; yanlış eski şifrede hata verir.
- [ ] Ollama kullanıyorsan Ayarlar → **⚡ OLLAMA'YI TEST ET**.
      **Beklenen:** Sunucu ve model durumunu gösterir.

---

## 14. Dayanıklılık / Hata Durumları (önemli!)

- [ ] Ollama'yı **kapat** (veya modeli çekme), motoru Ollama yap, mesaj at.
      **Beklenen:** Ekran takılmaz; anlaşılır bir hata mesajı gelir ("ollama pull …" gibi).
- [ ] İnternet **kapalıyken** Gemini ile mesaj at.
      **Beklenen:** Bağlantı hatası mesajı; ekran takılmaz.
- [ ] Sesli komutu, Ollama yavaşken/kapalıyken dene.
      **Beklenen:** "İŞLİYORUM"da **takılı kalmaz** — ya cevap ya da hata döner. *(Bu daha önce takılıyordu.)*
- [ ] Aynı anda arka arkaya hızlı birkaç mesaj at.
      **Beklenen:** "database is locked" hatası yok (WAL modu); hepsi işlenir.

---

## 15. Otomatik Testler

- [ ] Terminalde: `python tests/test_core.py`
      **Beklenen:** "TUM TESTLER GECTI (N/N)" — hata yok. (Hafıza, görev, plan, aksiyon protokolü,
      Ollama/embedding, ses, wake word, belge/RAG, hava/brifing/.ics, kesintisiz mod,
      sohbet geçmişi ve silinen-bilgi koruması dahil.)

---

## Not / Bilinen davranışlar

- İlk açılışta eski tek-parça sohbetin varsa GEÇMİŞ'te **"Önceki sohbet"** adıyla görünür.
- Görsel okuma için **Gemini API anahtarı** gerekir (Ollama-only modda görsel okunmaz, uyarı verir).
- `plyer` kurulu değilse Windows toast yerine **tepsi bildirimi** kullanılır (yine çalışır).
- Küçük yerel model (`llama3.2` 3B) Türkçede zayıf olabilir; donanımın uygunsa `qwen2.5:7b` öner.
