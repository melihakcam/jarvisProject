# Devam Notu — Jarvis Karşılaştırması ve Geliştirme Planı

> 18 Ekim 2026'da `D:\jarvisMirza` klasöründe yapılan sohbetin özeti.
> Yeni oturumda Claude Code'a: **"DEVAM_NOTU.md dosyasını oku, kaldığımız yerden devam edelim"** de.

## 1. Ne karşılaştırıldı?

| | Mirza (`D:\jarvisMirza`, PDF rehber) | Halil Özat (github.com/halilozat/jarvis) | **Bu proje (`D:\jarvisDeneme`)** |
|---|---|---|---|
| Ne | Sadece kurulum rehberi, kod yok | Hazır web uygulaması (Node/TS + React) | Çalışan Python asistan, Windows |
| Beyin | Claude Code + skill'ler | Abacus.AI RouteLLM API (ücretli anahtar) | Claude Code (`jarvis/brain.py` → `claude -p`) |
| Ses | Yerel (whisper / Piper) | Bulut (gpt-audio, Gemini TTS, ElevenLabs) | Yerel (Vosk + faster-whisper) |
| Arayüz | Terminal HUD | Web + telefon/tablet, grafik, Türkiye haritası | Tarayıcı paneli (localhost:5000) |
| Güçlü yanı | Obsidian hafıza fikri | Haber brifingi, sahne sahne görsel anlatım, kamera, akıllı ev, YouTube maç özeti | Bilgisayar kontrolü, ajanda, Google Takvim MCP, belge üretimi, ücretsiz |

**Karar:** Ana sistem bu proje (jarvisDeneme). Diğer ikisinden iyi fikirler alınacak.

## 2. Bilgisayardaki imkânlar

- **Claude Code** (abonelik): ana beyin.
- **Gemini Pro aboneliği**: API anahtarı değil. Yedek beyin için **Gemini CLI** (`npm install -g @google/gemini-cli`, `gemini -p "..."`) ya da aistudio.google.com'dan ücretsiz API anahtarı kullanılabilir.
- **Ollama** kurulu (`D:\Ollama`): `llama3.2:1b`, `qwen2.5:1.5b-instruct`, `gemma2:2b`, `codifya-router:tur2..tur6`. Bunlar küçük modeller, sohbet için zayıf ama **komut yönlendirme (router)** için uygun.
- Ayrıca `D:\Jarvis-dev`: Ollama tabanlı "analist" projesi (Tauri masaüstü). Ayrı bir proje.

## 3. Geliştirme planı (öneri sırası)

1. **Yedek beyin (Gemini):** `brain.py` içinde Claude çağrısı hata verirse, zaman aşımına uğrarsa ya da limit dolarsa `gemini -p` ile tekrar dene. Panelde hangi beynin cevap verdiğini göster.
2. **Hızlı yerel router (Ollama):** `commands.py` tanımadığı cümleleri Claude'a göndermeden önce `codifya-router` ya da `qwen2.5:1.5b` ile sınıflandır (komut mu, sohbet mi). Böylece basit işler internetsiz ve anında çalışır.
3. **Obsidian hafızası (Mirza'dan):** `kasa/ham`, `kasa/bilgi`, `kasa/cikti` klasörleri. Konuşmalar, notlar ve günlük özetler markdown olarak yazılsın; Jarvis buradan hatırlasın. Kasa bir git deposu olsun.
4. **Sabah brifingi (Halil'den):** "Jarvis, aydınlat beni" dediğinde haberler (RSS), hava durumu (Open-Meteo, anahtar gerekmez), ajanda ve takvim kısa ve sesli okunsun.
5. **Panelde görsel anlatım (Halil'den):** Brifing sırasında panelde sayılar, grafikler ve kaynak kartları belirsin.
6. **Günlük akış (Mirza'dan):** 07:00 sabah özeti, 19:00 günü kapatma. Mevcut ajanda ve hatırlatıcı sistemine bağlansın.
7. İsteğe bağlı: telefondan erişim (Cloudflare/Tailscale tüneli + erişim anahtarı), YouTube maç özeti.
8. **Doğal ses: Piper (Mirza'dan):** `jarvis/tts.py` şu an pyttsx3 (Windows SAPI, robotik ses) kullanıyor. Yerine yerel ve ücretsiz Piper Türkçe sesi (`tr_TR` modeli) gelsin. Piper kurulu değilse pyttsx3'e geri dönülsün.
9. **Skill yapısı (Mirza'dan):** İşler ayrı skill'lere bölünsün (ör. `gundem`, `plan`, `kasa`, `ajanda`, `belge`). Her skill'de tek bir `SKILL.md` olsun ve `description` alanında ne zaman kullanılacağı net yazsın. `CLAUDE.md` kişilik dosyası olarak kalsın.

### Mirza ile karşılaştırma özeti (madde 3, 6, 8, 9'un gerekçesi)

| Parça | Mirza | Bu proje | Durum |
|---|---|---|---|
| Beyin | Claude Code + 5 küçük skill | Claude Code + CLAUDE.md + `commands.py` (anında komutlar) | Bizimki hızlı, Mirza'nınki daha düzenli → madde 9 |
| Hafıza | Obsidian kasası, kalıcı | `data/konusmalar.json`, sadece son konuşmalar | Eksik → madde 3 |
| Kulak | whisper | Vosk + faster-whisper | Berabere |
| Ağız | Piper (doğal) | pyttsx3 (robotik) | Eksik → madde 8 |
| Yüz | Terminal HUD | Tarayıcı paneli | Bizimki önde |
| Bilgisayar kontrolü, ajanda, takvim, belge | Yok | Var | Bizimki önde |
| Günlük rutin | 07:00 / 09:00 / 14:00 / 19:00 akışı | Yok | Eksik → madde 6 |

## 4. Kurallar ve uyarılar

- Sesli cevaplar en fazla 3 cümle olsun (`CLAUDE.md`'deki kişilik kurallarına uy).
- `.gauth.json`, API anahtarları ve token'lar git'e girmesin (`.gitignore`'u kontrol et).
- Sohbette yanlışlıkla bir `mcp_token` paylaşıldı. Gerekirse ilgili servisten oturumu kapatıp yenile.

## 18 Ekim 2026 — ikinci oturum (jarvisDeneme)

**Kural:** Kullanıcı onaylamadan hiçbir dosya değiştirilmez. Önce plan sunulur, onay beklenir.

**Karar:** Gemini yedek beyin (madde 1) şimdilik ertelendi. Öncelik hız, token tasarrufu ve ses sorunları.

**Yapılanlar:**
- **Hız ve token** (`jarvis/brain.py`, `jarvis/config.py`): Sorular anahtar kelimeyle üç yola ayrılıyor.
  - Sohbet yolu: araçsız ve skill'siz.
  - Web yolu: yalnızca WebSearch ve WebFetch.
  - İşlem yolu: tüm araçlar açık.
  - Kelime listeleri `config.ISLEM_ANAHTAR_KELIMELER` ve `config.WEB_ANAHTAR_KELIMELER` içinde.
  - Kullanıcı ayarları ve eklentileri yüklenmiyor (`--setting-sources project,local`).
  - Bağlam 10 girişten 4'e indi.
  - Konsola `[Beyin] yol=… sure=…` satırı yazılıyor. İlk ölçümler: sohbet 5,2 sn, web 16,8 sn.
- **Susturma ve yankı** (`panel/index.html`):
  - Cevap cümle cümle okunuyor.
  - Mikrofon tuşuna ya da boşluğa basınca JARVIS hemen susuyor; konuşuyorduysa mikrofon 300 ms sonra açılıyor.
  - Esc tuşu ve SUSTUR düğmesi eklendi.
  - Duyulan metin JARVIS'in son söylediğine çok benziyorsa gönderilmiyor (yankı filtresi).
- **Kur, hava, haber yerelden** (`jarvis/guncel.py`, `commands.py`):
  - Kaynaklar: TCMB kur dosyası, `weather.py` ve AA RSS (yedeği TRT RSS).
  - Bir saniyenin altında cevap veriyor, sıfır token harcıyor.
  - Başka şehir, yorum ya da belirli konu soruları Claude'a gidiyor.
- **Hava konumu sabit Konya:** `config.HAVA_KONUMU`. `None` yapılırsa konum IP adresinden bulunur.
- **Sohbet yolu inceltildi:**
  - Claude Code'un varsayılan talimatı yerine yalnızca JARVIS talimatı gidiyor; token yaklaşık 5.400'den 2.070'e indi.
  - Tarih ve saat soruya ekleniyor.
- **Hazır bekleyen Claude** (`brain.onceden_hazirla`, `config.BEYIN_HAZIR_BEKLET`):
  - Bir sonraki sohbet sorusu için Claude süreci önceden açılıyor. Her süreç tek soru cevaplıyor, token birikmiyor.
  - Sohbet süresi yaklaşık 3,5 sn'den 1,7 sn'ye indi.
  - Hazır süreç yoksa normal çağrıya düşülüyor.
- **"Aç" hatası düzeltildi:** "olacak", "kaç" gibi kelimelerin içindeki "ac" harfleri artık bir şey açtırmıyor; "aç" ayrı kelime olmalı.
- **Kendini tanıtma:** "Sen kimsin" ya da "kendini tanıt" denince "Ben JARVIS, Melih Akçam'ın sesli kişisel asistanıyım efendim." deniyor.
- **Seslenme:** Yalnızca "Jarvis" ya da "Hey Jarvis" denince "Emirlerinizi bekliyorum efendim." deniyor.
  - Ses tanıma bazen "Jerry" ya da "Cervis" gibi yanlış yazıyor. Bunlar panelde cümle başında "Jarvis" olarak düzeltiliyor (`adiDuzelt`).
- **İngilizce:**
  - Paneldeki TR/EN düğmesiyle ya da "İngilizce konuş" / "speak Turkish" komutlarıyla dil değişiyor.
  - Whisper Türkçe ile İngilizce arasında kendisi seçim yapıyor.
  - "Open / close YouTube, notepad…" komutları çalışıyor.
  - Kullanıcı ağırlıklı olarak Türkçe kullanacak.
- **Aç/kapat istekleri işlem yoluna gidiyor:** Hızlı komutun çözemediği "aç", "kapat", "open" istekleri Claude'un araçlı yoluna gidiyor ve orada gerçekten yapılıyor (yaklaşık 6-7 sn). Sohbet yolundaki Claude'a "yapamadığın işi yapıyorum deme" talimatı eklendi.
- **Noktalama:** Soru işareti ve nokta komutları bozmuyor (`commands._normalize`).
- **Edge ses tanıması:** Tek bir hatada Whisper'a kalıcı geçilmiyor; üst üste 3 hata gerekiyor.

**Denendi ve vazgeçildi: doğal ses.**
- Piper'ın tek Türkçe sesi (dfki) beğenilmedi.
- Edge "Ahmet" sesi beğenildi ama güvenilmez çıktı: sık sık ses vermedi, cümle başına 4 sn'ye kadar bekletti.
- Hepsi kaldırıldı (paketler, model, kod). Ses yine Windows Tolga.
- Not: Panel İngilizce moddayken seçilen Edge İngilizce sesi kullanıcıya çok iyi geliyor. Türkçe için de çok dilli bir Edge sesi denenebilir; önce panelde seçilen sesin adı günlüğe yazdırılıp öğrenilmeli.

- **Sunum hazırlığı:**
  - "Sen kimsin", "kendini tanıt", "ne yapabilirsin", "hey Jarvis" ve "YouTube'u aç" Claude'a gitmeden, anında ve sabit cevapla çalışıyor.
  - "Ne yapabilirsin" cevabı JARVIS'in bütün yeteneklerini sayıyor. Sohbet yolundaki Claude da kısıtlamalarından bahsetmiyor.
- **Ajanda:**
  - "… ajandama ekle / yaz / kaydet" cümleleri de hatırlatıcı kuruyor. "Ajandamda ne var" sorusu bugünkü kayıtları okuyor.
  - Masaüstü uygulaması artık hatırlatıcı bekçisini başlatıyor; saati gelen hatırlatıcı sesli okunuyor. Bu, uygulama çalışırken henüz denenmedi.
- **Edge gecikmesi:** Tuş bırakıldıktan sonra Edge 1,5 sn içinde sonucu vermezse panel ekrandaki metni kendisi gönderiyor. Hiçbir şey duyulmazsa "Sizi duyamadım" yazıyor.

## Bilinen sorunlar

- **Whisper ön yüklemesi masaüstü uygulamasında yapılmıyor.** `server._onisitma` çağrılmıyor; Whisper ilk kullanıldığında yükleniyor.
- **İngilizce modda Edge ses tanıması bazen hiç sonuç vermiyor.** Bu durumda panel hiçbir tepki göstermiyor. Önerilen çözüm: İngilizce modda dinlemeyi Whisper'a vermek ve boş sonuçta "duyamadım" yazmak. Kullanıcı şimdilik istemedi.

## Yeni öncelik sırası

1. **Sabah brifingi ve günlük akış** (madde 4 ve 6). Kur, hava ve haber parçaları artık hazır; 07:00 ve 19:00'da otomatik okunabilir.
2. **Konuşmaya erken başlama.** Cevap akış (stream) olarak alınır, ilk cümle hazır olunca okunur.
3. **Akıllı hafıza** (madde 3). Claude'a yalnızca soruyla ilgili notlar gider.
4. **Panelde brifing görselleri** (madde 5).
5. **Ertelenenler:** Gemini yedek beyin, doğal ses, Ollama yönlendirici, skill yapısı (token artırıyor), telefondan erişim, YouTube maç özeti, sürekli dinleyen "Hey Jarvis" (şu an bas-konuş ile çalışıyor).

## Sıradaki adım

Kullanıcı 19 Ekim'de JARVIS'i bir sunumda kullanacak. Sunum öncesinde kullanılacak cümleler denenmeli; internet bağlantısı gerekli. Sunumdan sonra önce hatırlatıcının gerçekten çaldığı doğrulanacak ("2 dakika sonra test hatırlat"). Ardından öncelik sırasının birinci maddesiyle (sabah brifingi) devam edilecek.
