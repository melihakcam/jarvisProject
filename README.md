# JARVIS — Kurulum ve Çalıştırma

Kişisel sesli asistan. Genel tanıtım için [`tanitim.md`](./tanitim.md) dosyasına bakın.

## Gereksinimler

- **Windows 10/11**
- **Python 3.9+** — <https://www.python.org/downloads/> (kurulumda "Add to PATH" işaretleyin)
- **Claude Code** — beyin olarak kullanılır (mevcut aboneliğiniz yeterli)
  ```bash
  npm install -g @anthropic-ai/claude-code
  ```
- **Mikrofon ve hoparlör**

## Kurulum

1. Python paketlerini kurun:
   ```bash
   pip install -r requirements.txt
   ```

2. Vosk Türkçe ses modelini indirin (Aşama 3'te otomatik betikle de yapılabilir):
   - <https://alphacephei.com/vosk/models> adresinden `vosk-model-small-tr` indirin
   - `models/` klasörüne çıkarın

3. Claude Code'un çalıştığını doğrulayın:
   ```bash
   claude --version
   ```

## Çalıştırma

### 🎛️ Panel modu (önerilen — hiç pencere açmaz)
`scripts/jarvis_baslat.vbs` dosyasına **çift tıklayın** (hiç pencere açmaz) ya da
`scripts/jarvis_baslat.bat` kullanın. Sunucu arka planda başlar ve **kontrol
paneli tarayıcıda açılır** (http://localhost:5000).

Bu betik sanal ortamı, model önbelleğini ve geçici dosyaları **D: sürücüsünde**
tutar (`D:\jarvis-env`, `D:\jarvis-cache`); C: sürücüsüne hiçbir şey yazılmaz.

> İpucu: dosyaya sağ tık → "Kısayol oluştur" → kısayolu masaüstüne taşıyın.

- **Konuşmak için:** Panel açıkken **mikrofon butonuna basılı tutun** (veya
  **BOŞLUK tuşuna** basılı tutun), konuşun, bırakın.
- **Yazmak için:** Mikrofonun altındaki metin kutusuna komut yazıp Enter'a basın.
  Sesle söylenmesi zor şeyler (örn. YouTube linki) için bunu kullanın.
- JARVIS panelde yazıyla gösterir **ve sesli cevap verir**.
- Hatırlatıcı/ajanda panelde canlı görünür; kayıtlar `data/ajanda.json`
  dosyasında tutulur (panelden veya sesle düzenlenir).

### 💻 Terminal modu (alternatif)
```bash
python jarvis/main.py
```
Boşluk tuşuna basılı tutup konuşun. Çıkış: `Ctrl+C` veya "kapan" komutu.

## 🎙️ Sesli Komutlar (bilgisayar kontrolü)

Bu komutlar **anında, internetsiz** çalışır (Claude'a gitmeden). Tanınmayan her şey
otomatik olarak beyne (Claude) sorulur ve akıllıca cevaplanır.

| Söyle | Yapar |
|-------|-------|
| "saat kaç" / "bugün günlerden ne" | Saat ve tarihi söyler |
| "not defterini aç", "hesap makinesini aç", "chrome aç" | Uygulama açar |
| "youtube aç", "gmail aç", "github aç" | Siteyi açar |
| "not defterini kapat", "chrome kapat" | Uygulamayı kapatır |
| "internette ... ara", "... arat" | Google'da arar |
| "... dosyasını bul" | Masaüstü/Belgeler/İndirilenler'de arar, Gezgin'de gösterir |
| "sesi aç/kıs", "sesi kapat", "sustur" | Ses seviyesi |
| "duraklat", "oynat", "sonraki şarkı" | Medya kontrolü |
| "pencereleri küçült", "masaüstünü göster", "tam ekran" | Pencere yönetimi |
| "bilgisayarı kilitle" | Ekranı kilitler |
| "15:30'da toplantı hatırlat", "20 dakika sonra çayı al hatırlat" | Ajandaya kayıt ekler, zamanı gelince sesli hatırlatır |
| "masaüstünü düzenle", "indirilenler klasörünü düzenle" | Klasördeki dosyaları türüne göre alt klasörlere ayırır (Resimler, Belgeler, Videolar...) |
| YouTube linki + "özetle" | Videonun transkriptini indirip özetler (panelin metin kutusuna linki yapıştırın; internet ve Claude gerekir) |
| "bana bir Word raporu hazırla", "şu tabloyu Excel yap" gibi belge istekleri | JARVIS (Claude beyni), docx/pdf/pptx/xlsx skillerini kullanarak dosyayı oluşturup Masaüstüne kaydeder |
| Bunların dışında her soru | JARVIS (Claude beyni) cevaplar |

Yeni komut eklemek/değiştirmek için: `jarvis/commands.py`.

## 🎛️ Kontrol Paneli

Panel, sunucu çalışırken http://localhost:5000 adresinde açılır. Gösterdiği
**tüm veriler gerçektir** — hiçbir kart simülasyon değildir:

| Kart | Kaynak |
|------|--------|
| Sistem yaşam belirtileri | `psutil` (CPU, bellek, disk, batarya) + Windows GPU performans sayacı |
| Ağ trafiği | `psutil` bayt sayaçları; PING gerçek ICMP/TCP ölçümü |
| Hava durumu | IP'den konum + [Open-Meteo](https://open-meteo.com) (anahtar gerekmez) |
| Bağlantı durumları | Gerçek kontroller: internet, ağ geçidi, mikrofon, STT modeli, Claude CLI |
| Bugünün ajandası | `data/ajanda.json` — panelden veya sesle eklenir, zamanı gelince sesli çalar |
| Dikkat gerektiren | Gerçek disk/bellek/batarya/ağ durumundan üretilir |
| Sistem kaydı | Yalnızca gerçekleşen olaylar (yedekleme, hatırlatıcı, STT, komutlar) |

Hızlı komut butonları da gerçek işlem yapar:

| Buton | Yaptığı |
|-------|---------|
| ODAK MODU | Windows bildirim balonlarını gerçekten kapatır/açar (kayıt defteri) |
| BRİFİNG / BRIEF ME | Saat, hava, ajanda ve sistem durumundan gerçek özet üretip seslendirir |
| YEDEKLE | Projeyi ve verileri `D:\jarvis-backups` altına zip'ler |
| KİLİTLE | Windows oturumunu kilitler |

İlgili modüller: `jarvis/telemetry.py`, `jarvis/weather.py`, `jarvis/ajanda.py`,
`jarvis/eylemler.py`.

## 🔌 MCP Bağlantıları (Google Takvim)

JARVIS, takviminize MCP üzerinden erişebilir: "yarın toplantım var mı",
"salı 15:00'e diş randevusu ekle" gibi komutlar.

**Hız notu:** MCP sunucuları her çağrıda yeniden yüklenir ve bu birkaç saniye
ekler. Bu yüzden MCP **sadece gerektiğinde** açılır — soruda "takvim",
"toplantı", "randevu", "mail" gibi bir kelime geçmiyorsa hızlı yol kullanılır.
Bu kelimeler `jarvis/config.py` içindeki `MCP_ANAHTAR_KELIMELER` listesinden
düzenlenebilir; `MCP_ACIK = False` ile MCP tamamen kapatılabilir.

### Kurulum (tek seferlik, ~10 dakika)

1. <https://console.cloud.google.com> adresinde bir proje oluşturun.
2. **Google Calendar API**'yi etkinleştirin.
3. *Kimlik Bilgileri* → *Kimlik Bilgisi Oluştur* → *OAuth istemci kimliği*:
   - Uygulama türü: **Desktop app** (masaüstü uygulaması) — bu önemli
4. Kapsam (scope) olarak şunları ekleyin:
   `https://www.googleapis.com/auth/calendar` ve
   `https://www.googleapis.com/auth/calendar.events`
5. *Hedef Kitle* ekranında kendi e-posta adresinizi **test kullanıcısı** olarak ekleyin.
6. İndirdiğiniz JSON dosyasını proje köküne **`.gauth.json`** adıyla kaydedin
   (biçim için `.gauth.ornek.json` dosyasına bakın).
7. Yetkilendirmeyi başlatın — tarayıcı açılır, Google hesabınızla izin verirsiniz:
   ```bash
   npx @cocal/google-calendar-mcp auth
   ```
8. Proje MCP sunucusunu **bir kez onaylayın**: proje klasöründe `claude` komutunu
   çalıştırıp çıkan onay sorusuna olur verin. Onaylanmadan sunucu "pending
   approval" durumunda kalır ve beyin araçları göremez.

> **Not:** Claude uygulamasında hesabınıza bağlı "claude.ai Gmail / Google
> Calendar" bağlayıcıları görünebilir. Bunlar yalnızca uygulama içi oturumda
> çalışır; JARVIS'in kullandığı başlıksız (`claude -p`) çağrılara araç olarak
> açılmazlar. Bu yüzden yukarıdaki proje sunucusu kurulumu gereklidir.

> ⚠️ **Güvenlik:** `.gauth.json` ve üretilen jeton dosyaları takviminize erişim
> verir. Bunlar `.gitignore`'da tanımlıdır ve **asla depoya gönderilmemelidir**.

### Neden sadece Takvim, Gmail yok?

Gmail + Takvim'i birlikte sunan `mcp-google-workspace` npm paketi incelendiğinde,
işaret ettiği kaynak deposunun (`VSF-TTS/AI-Platform-A`) **erişilemez (404)**
olduğu görüldü; yayıncısı, dokümantasyonunu okuduğumuz açık kaynak projeyle
(`j3k0/mcp-google-workspace`) aynı değil. Gmail bağlantısı `https://mail.google.com/`
kapsamı ister — yani **tüm e-postaları okuma, gönderme ve silme** yetkisi. Kaynağı
doğrulanamayan bir pakete bu yetki verilmedi.

Gmail'i yine de bağlamak isterseniz güvenli yol, `j3k0/mcp-google-workspace`
deposunu **kaynaktan kurmaktır** (klonlayıp `npm install && npm run build`),
npm'deki aynı adlı paketi kullanmak değil.

## Bileşenleri tek tek test etme

| Komut | Ne test eder |
|-------|--------------|
| `python jarvis/tts.py` | Sesli çıkış (JARVIS konuşur) |
| `python jarvis/stt.py` | Sesli giriş (konuşmanızı yazıya döker) |
| `python jarvis/brain.py "merhaba"` | Beyin (Claude'dan cevap) |
| `python jarvis/main.py` | Uçtan uca tam sistem |

## Maliyet

Mevcut Claude aboneliğiniz dışında **ücret yoktur**. Tüm ses araçları ücretsiz ve
offline çalışır.

## Yol Haritası

Detaylı yol haritası ve kararlar için `tanitim.md` içindeki "Yol Haritası" bölümüne bakın.
