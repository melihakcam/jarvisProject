# 🤖 JARVIS — Kişisel Sesli Asistan

> "Tabii efendim."

JARVIS; Windows bilgisayarında çalışan, **sesle yönetilen kişisel bir yapay zekâ
asistanıdır**. Bilgisayarını sesle kontrol eder, sorularını cevaplar, sana hatırlatır,
kod yazmana yardım eder ve eklediğin **MCP bağlantıları** ile gerçek işler yapar.

---

## 🎯 Amaç

Tony Stark'ın JARVIS'i gibi, senin kişisel dijital asistanın olmak. Konuşarak komut
verirsin, o da resmi ve efendi bir üslupla yanıtlar ve işleri halleder.

## 🧠 Nasıl Çalışır? (Mimari)

```
🎙️  Mikrofon
     │  (tuşa bas — push-to-talk)
     ▼
📝  Ses → Yazı        (Vosk — offline, ücretsiz, Türkçe)
     │
     ▼
🧠  BEYİN: Claude Code   (claude -p — mevcut abonelik, ekstra ücret yok)
     │
     ▼
🔊  Yazı → Ses        (pyttsx3 — Windows'un dahili sesi, ücretsiz)
     │
     ▼
📢  Hoparlör
```

JARVIS'in "beyni" **Claude Code**'dur — yani şu an bu projeyi kuran araç. Ekstra bir
yapay zekâ API'si satın almana gerek yoktur; mevcut Claude aboneliğin kullanılır.

## ✨ Yetenekler

| Yetenek | Açıklama | Durum |
|---------|----------|-------|
| 🎙️ Sesli komut | Konuşarak komut verme (push-to-talk) | Aşama 3 |
| 🔊 Sesli yanıt | JARVIS'in sesli cevap vermesi | Aşama 2 |
| 💬 Soru-cevap | Her konuda akıllı yanıtlar | Aşama 4 |
| 💻 Bilgisayar kontrolü | Uygulama açma/kapama, dosya bulma, pencere kontrolü | Aşama 6 |
| 🔍 İnternette arama | Web'de arama yapma | Aşama 6 |
| 👨‍💻 Kod yardımı | Kod yazma ve açıklama | Aşama 4 |
| ⏰ Hatırlatıcı | Görev ve hatırlatmalar | Sonraki |
| 🔌 MCP bağlantıları | Gmail, Notion, GitHub vb. (sen eklersin) | Sonraki |

## 🗣️ Kişilik ve Dil

- **Üslup:** Resmi, efendi, film JARVIS'i gibi ("Tabii efendim", "Hemen efendim").
- **Dil:** Türkçe ve İngilizce. Hangisiyle konuşursan o dilde yanıtlar; istediğinde
  dili değiştirebilirsin.
- **Tavır:** Kısa, net, saygılı. Gereksiz uzatmaz.

## 💰 Maliyet

- **Parasal:** Mevcut Claude aboneliğin dışında **0 ₺**. Ücretli hiçbir API kullanılmaz
  (Fish Audio, ElevenLabs, OpenAI vb. yok).
- **Sistem yükü:** Çok düşük. Beyin bulutta çalışır; bilgisayarında sadece hafif ses
  araçları (Vosk + pyttsx3) döner.

## 🧰 Kullanılan Ücretsiz Araçlar

| Araç | Görevi | Ücret |
|------|--------|-------|
| [Claude Code](https://claude.ai/code) | Beyin (düşünme, cevap) | Mevcut abonelik |
| [Vosk](https://alphacephei.com/vosk/) | Ses → Yazı (offline) | Ücretsiz |
| [pyttsx3](https://pypi.org/project/pyttsx3/) | Yazı → Ses (Windows sesi) | Ücretsiz |
| Python | Bilgisayar kontrolü & tutkal | Ücretsiz |

## 🗺️ Yol Haritası

1. ✅ **İskelet + dokümanlar** — bu dosya, kişilik (`CLAUDE.md`), kurulum notları
2. ✅ **Sesli çıkış (TTS)** — JARVIS konuşuyor (Türkçe "Tolga" sesi)
3. ✅ **Sesli giriş (STT)** — sen konuş, JARVIS yazıya döküyor (Vosk)
4. ✅ **Beyin bağlantısı** — Claude Code'a soru sorup cevap alıyor
5. ✅ **Ana döngü** — tuşa bas → konuş → sesli cevap
6. ✅ **Yerel komutlar** — uygulama açma/kapama, dosya bulma, arama, ses/medya, pencere
7. ✅ **Gösterge paneli** — sinematik JARVIS arayüzü (canlı saat + hatırlatıcılar)
8. 🔶 **MCP bağlantıları** — altyapı hazır: MCP yalnızca e-posta/takvim konulu
   sorularda açılır (hız kaybı olmasın diye). Google Takvim tanımlı; kullanmak
   için OAuth kurulumu gerekir (bkz. `README.md`). Gmail, güvenilir bir paket
   bulunamadığı için henüz bağlanmadı.

## 🔒 Güvenlik İlkesi

> **Önce oku, sonra yaz. Önce test et, sonra yetki ver.**

MCP bağlantıları eklenirken her araç önce yalnızca **okuma** yetkisiyle test edilir.
Yazma, silme, gönderme gibi işlemler için JARVIS **önerir**, son kararı **sen verirsin**.
E-posta gönderme, dosya silme gibi işlemler her zaman senin onayınla yapılır.

---

*Kurulum ve çalıştırma talimatları için `README.md` dosyasına bakın.*
