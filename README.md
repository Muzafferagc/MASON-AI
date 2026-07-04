# MASON AI 🤖

Jarvis benzeri, hiçbir şeyi unutmayan kişisel yapay zeka asistanın.
**Şu an:** Chat + Kalıcı Hafıza + Planlama + Anlamsal Arama + Sesli Konuşma + "Hey Mason".
(Yol haritası için `ROADMAP.md`'ye bak.)

## Kurulum (Windows)

### 1. Python kur (zaten varsa atla)
[python.org/downloads](https://www.python.org/downloads/) → indir → kurulumda
**"Add Python to PATH"** kutusunu mutlaka işaretle.

### 2. Gerekli paketleri kur
Proje klasöründe bir komut istemi (cmd) aç ve:
```
pip install -r requirements.txt
```

### 3. Ücretsiz Gemini API anahtarı al
1. [aistudio.google.com](https://aistudio.google.com) → Google hesabınla gir
2. **"Get API key"** → **"Create API key"** → kopyala
3. Kredi kartı istemez; ücretsiz kota günlük kullanım için fazlasıyla yeter

### 4. Çalıştır
```
python run.py
```
İlk açılışta ayarlar penceresi otomatik açılır → API anahtarını yapıştır → Kaydet.
Hepsi bu! Mason'la konuşmaya başla. 🎉

## Sesli konuşma 🎤 (Faz 2)
- **Konuşmak için:** giriş kutusunun yanındaki 🎤'a tıkla, konuş, bitince tekrar tıkla.
  Mason konuşmanı yazıya çevirip cevaplar. *(İlk kullanımda ~460 MB'lık ses tanıma
  modeli bir kez indirilir — biraz bekle.)*
- **Sesli yanıt:** Mason cevaplarını sesli okur. Sağ üstteki 🔊 ile aç/kapat.
- Ses paketleri kurulmazsa Mason yine çalışır; sadece ses butonları kapalı olur.

## "Hey Mason" 🎙️ (Faz 3)
Uygulama açıkken (pencere gizli olsa bile) **"Hey Mason"** de:
- Sadece "Hey Mason" dersen → Mason "Efendim?" der, ~12 saniye içinde komutunu söyle
- "Hey Mason, bugün ne yapmalıyım?" gibi tek nefeste de sorabilirsin
- Pencereyi kapatınca Mason sistem tepsisine (saat yanındaki ikonlara) gizlenir ve
  dinlemeye devam eder. Tamamen kapatmak: tepsideki ikona sağ tık → Kapat
- Ayarlardan (⚙) "Hey Mason ile uyanma" kapatılabilir

**Windows açılınca otomatik başlasın:**
1. `start_mason.bat` dosyasına sağ tık → "Kısayol oluştur"
2. Win+R → `shell:startup` → Enter
3. Kısayolu açılan klasöre taşı. Hepsi bu — artık PC açılınca Mason hazır.

## Alternatif: Ollama (internet/anahtar gerektirmez)
1. [ollama.com](https://ollama.com) → indir, kur
2. Komut isteminde: `ollama pull llama3.2`
3. Mason'da ⚙ Ayarlar → motor olarak **Ollama** seç

## Mason'a örnek şeyler söyle
- *"Önümüzdeki hafta vize haftam, pazartesi matematik çarşamba fizik sınavım var"* → hafızasına kaydeder, görev açar
- *"Bu haftayı planlar mısın?"* → önceliklere göre haftalık plan yapar ve kaydeder
- *"MASON projemde ses özelliği eklemek istiyorum"* → proje ağacına dal ekler
- *"Bugün ne yapmalıyım?"* → görevlerine ve hafızasına bakarak önerir

## Dosya yapısı
```
run.py              → uygulamayı başlatır (pencere + JS köprüsü)
mason/config.py     → ayarlar (config.json)
mason/database.py   → SQLite tabloları (hafıza, görevler, mesajlar, planlar)
mason/memory.py     → kalıcı hafıza (ağaç yapısı)
mason/planner.py    → görev ve plan motoru
mason/llm.py        → Gemini / Ollama sağlayıcıları
mason/embeddings.py → anlamsal hafıza araması (Faz 1.5)
mason/voice.py      → mikrofon + Whisper + sesli yanıt (Faz 2)
mason/wakeword.py   → "Hey Mason" algılama (Faz 3)
start_mason.bat     → konsolsuz başlatma / Windows açılışı için
mason/agent.py      → Mason'un beyni: prompt + aksiyon protokolü
ui/index.html       → Jarvis temalı arayüz
tests/test_core.py  → testler (python tests/test_core.py)
```
Verilerin `mason.db` dosyasında saklanır — **bu dosyayı silme**, Mason'un hafızası orada!

## Sorun giderme
- **"pip tanınmıyor"** → Python'u PATH işaretli yeniden kur
- **Gemini hatası 400/403** → API anahtarını kontrol et
- **Gemini hatası 404** → Ayarlardan model adını güncelle (eski model kapanmış olabilir)
- **Gemini hatası 429** → günlük ücretsiz kota doldu; yarın sıfırlanır veya Ollama'ya geç
- **Pencere açılmıyor** → `pip install pywebview --upgrade`
- **"Hey Mason" tepki vermiyor** → net ve normal ses tonuyla söyle; ilk algılama
  model yüklemesi yüzünden ~10 sn gecikebilir. Ortam çok gürültülüyse zorlanabilir
- **Mikrofon çalışmıyor** → Windows Ayarlar → Gizlilik → Mikrofon izinlerini kontrol et
- **Ses paketleri kurulamadı** → sorun değil; Mason yazılı modda çalışmaya devam eder
