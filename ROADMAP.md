# MASON AI — Yol Haritası

> **Proje:** AI Planning and Schedule for MASON AI
> **Sahibi:** Muzaffer — Akdeniz Üniversitesi, AI & Data Engineering
> **Hedef:** Jarvis benzeri, hiçbir şeyi unutmayan, hayatını planlayan kişisel yapay zeka asistanı
> **Bütçe:** 0 TL — tamamen ücretsiz araçlarla

---

## Genel Mimari

```
┌─────────────────────────────────────────────┐
│              MASON Masaüstü Uygulaması       │
│                                             │
│  ┌───────────┐   ┌──────────────────────┐   │
│  │  Chat UI  │◄──│   Agent (Mason'un     │   │
│  │ (Jarvis   │   │   karar mekanizması)  │   │
│  │  teması)  │   └──────┬───────────────┘   │
│  └───────────┘          │                   │
│                ┌────────┼────────┐          │
│                ▼        ▼        ▼          │
│          ┌────────┐ ┌───────┐ ┌────────┐    │
│          │ Hafıza │ │Planla-│ │  LLM   │    │
│          │(SQLite)│ │ yıcı  │ │katmanı │    │
│          └────────┘ └───────┘ └───┬────┘    │
└───────────────────────────────────┼─────────┘
                                    ▼
                     Gemini API (ücretsiz kota)
                     veya Ollama (yerel model)
```

**Hafıza sistemi (projenin kalbi):** Mason her konuşmadan önemli bilgileri
otomatik çıkarıp SQLite veritabanına kaydeder. Her hafıza bir kategoriye
(proje / hedef / tercih / bilgi) ve istenirse bir projeye bağlanır — senin
"ağaç dalları" fikrin. Yeni mesaj geldiğinde ilgili hafızalar aranıp
Mason'un beynine (LLM'e) verilir. Böylece detaylar asla silinmez.

---

## Faz 1 — MVP: Chat + Hafıza + Planlama ✅ TAMAMLANDI

**Ne yapar:**
- Jarvis tarzı koyu temalı masaüstü chat uygulaması (Türkçe + İngilizce)
- Kalıcı hafıza: projelerini, hedeflerini, tercihlerini kaydeder, unutmaz
- Görev yönetimi: görev ekler, önceliklendirir, tarih atar
- Planlama: günlük / haftalık / aylık plan üretir, önem sırasına dizer
- Konuşma geçmişi kalıcıdır — uygulamayı kapatsan da hatırlar

**Teknolojiler:** Python, pywebview (pencere), SQLite (veritabanı),
Gemini API ücretsiz kotası veya Ollama.

**Öğreneceklerin:** Python proje yapısı, SQLite, REST API kullanımı,
LLM prompt tasarımı, JSON ile "tool calling" mantığı.

## Faz 1.5 — Akıllı Hafıza Araması (embeddings / RAG) ✅ TAMAMLANDI

- Hafızalar "embedding" denen sayısal vektörlere çevrilir
- Kelime eşleşmesi yerine **anlam** benzerliğiyle arama yapılır
  (örn. "okul projesi" ararsın, "üniversite ödevi" kaydını bulur)
- Gemini'nin ücretsiz embedding API'si kullanılır
- **Öğreneceklerin:** Embeddings, vektör benzerliği (cosine similarity), RAG

## Faz 2 — Ses: Mason'la Konuşma ✅ TAMAMLANDI

- **Kulak:** Whisper (OpenAI'ın açık kaynak, ücretsiz, yerel çalışan
  ses→yazı modeli) — Türkçe ve İngilizce anlar
- **Ağız:** edge-tts (Microsoft'un ücretsiz doğal seslendirmesi) —
  Mason gerçekçi bir sesle cevap verir
- Mikrofon butonu ile konuş, Mason sesli yanıtlasın
- **Öğreneceklerin:** Ses işleme, STT/TTS, asenkron programlama

## Faz 3 — "Hey Mason": Gerçek Jarvis Deneyimi ✅ TAMAMLANDI

- **Wake word:** Whisper (tiny) tabanlı "Hey Mason" algılama — ekstra kurulum
  gerektirmez, tamamen yerel ve ücretsiz. (El şaklatma bilinçli olarak yapılmadı:
  yanlış tetiklenmeye çok açık; kelime tabanlı uyanma endüstri standardı.)
  İleride istersen openWakeWord ile özel eğitilmiş model de takılabilir.
- Windows başlangıcında arka planda sessizce çalışır (system tray)
- Eller serbest tam sesli sohbet döngüsü
- **Öğreneceklerin:** Arka plan servisleri, sürekli ses akışı işleme

## Faz 4 — Genişleme (MASON'un geleceği)

Çekirdek sağlam olunca eklenebilecekler:
- Takvim entegrasyonu (Google Calendar)
- Dosya ve bilgisayar kontrolü ("Mason, projemi aç")
- Proaktif hatırlatmalar ("Bugün X'in son günü")
- Ders çalışma analizi, pomodoro, alışkanlık takibi
- Uzun vadeli hedef takibi ve ilerleme raporları

---

## Ücretsiz Kalma Stratejisi

| İhtiyaç | Ücretsiz çözüm |
|---|---|
| LLM (beyin) | Gemini API ücretsiz kotası *(günlük cömert limit)* veya Ollama (tamamen yerel) |
| Veritabanı | SQLite (Python'a gömülü) |
| Embeddings | Gemini embedding API (ücretsiz) |
| Ses→Yazı | Whisper (açık kaynak, yerel) |
| Yazı→Ses | edge-tts (ücretsiz) |
| Wake word | openWakeWord (açık kaynak) |

**Ollama nedir?** Bilgisayarına kurduğun, LLM'leri tamamen yerel ve ücretsiz
çalıştıran bir program (ollama.com). İnternet gerektirmez, tamamen özel.
Dezavantajı: küçük modeller Gemini kadar akıllı değildir ve hızı senin
donanımına bağlıdır. Bu yüzden ana motor Gemini, yedek Ollama.
