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
