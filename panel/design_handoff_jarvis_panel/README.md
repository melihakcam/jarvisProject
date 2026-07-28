# Handoff: J.A.R.V.I.S Kontrol Paneli

## Overview
Tek ekranlık, sinematik bir kişisel komuta paneli ("Jarvis"). Ekranın merkezinde canlı bir enerji çekirdeği, çevresinde sistem telemetrisi, bağlantı durumları, sesli komut arayüzü, günlük ajanda, uyarılar ve akan sistem kaydı bulunur. Mikrofon açıldığında gerçek mikrofon girişi (Web Audio) çekirdeği ve dalga formunu canlı olarak sürer.

## About the Design Files
Bu pakette bulunan dosya bir **tasarım referansıdır** — HTML ile yapılmış, hedeflenen görünüm ve davranışı gösteren bir prototip; doğrudan kopyalanacak üretim kodu değildir. Görev, bu tasarımı hedef kod tabanının mevcut ortamında (React, Vue, SwiftUI, native vb.) o projenin yerleşik desenleri ve kütüphaneleriyle **yeniden inşa etmektir**. Henüz bir ortam yoksa, proje için en uygun çerçeveyi seçip tasarımı orada uygulayın.

Not: dosya `.dc.html` uzantılıdır ve bir streaming-template runtime'ı kullanır (`{{ hole }}` yer tutucuları, `<sc-for>`, `<sc-if>`). Bunlar sırasıyla normal interpolasyon, liste map'i ve koşullu render'a karşılık gelir; runtime'ı taşımayın, karşılığını hedef çerçevede yazın. Dosyanın sonundaki `class Component` bloğu tüm durum ve zamanlayıcı mantığını içerir.

## Fidelity
**High-fidelity.** Renkler, tipografi, boşluklar, animasyon süreleri ve etkileşimler nihai haldedir; birebir yeniden üretilmelidir.

## Screens / Views

### Tek ekran: Kontrol Paneli
- **Purpose**: Kullanıcı sistemine tek bakışta hakim olur, sesli komut verir, günlük brifing alır.
- **Layout**: Dış sarmalayıcı `position:relative; min-height:100vh; padding:22px 26px 18px; overflow-x:auto; overflow-y:hidden`. Arka plan `radial-gradient(1200px 700px at 50% 42%, #0b2740 0%, #061424 45%, #03070e 100%)`.
  - Dekoratif katman 1: 64×64px grid (yatay+dikey `rgba(95,224,255,.5)` 1px çizgiler), `opacity:.16`, merkezden dışa radial mask.
  - Dekoratif katman 2: üstten aşağı akan 2px tarama çizgisi, `jscan 9s linear infinite`.
  - Header: flex, wrap, space-between, `gap:16px 24px`, altında `1px solid rgba(95,224,255,.18)` çizgi.
  - Main: `display:grid; grid-template-columns:minmax(240px,300px) minmax(300px,1fr) minmax(260px,320px); gap:18px; align-items:start`.
  - Footer: log şeridi, `1px solid rgba(95,224,255,.16)`, `rgba(6,20,34,.6)` zemin.

- **Components**:
  - **Wordmark bloğu (sol üst)**: 44×44px dönen iki halka (6s ileri / 9s geri) + merkezde 10px camgöbeği nokta (`box-shadow:0 0 14px 4px rgba(95,224,255,.7)`). Yanında "J.A.R.V.I.S" — Rajdhani 700, 26px, `letter-spacing:.42em`, `#eaf9ff`, `text-shadow:0 0 18px rgba(95,224,255,.45)`; altında "KİŞİSEL KONTROL ARAYÜZÜ · v9.4" — JetBrains Mono 10px, `.28em`, `rgba(160,215,240,.6)`.
  - **Durum çipleri**: "TÜM SİSTEMLER AKTİF" (yeşil 7px nokta, `jblink 2.4s steps(1,end) infinite`, çerçeve `rgba(95,224,255,.25)`) ve "GÜVENLİ HAT · AES-512" (amber çerçeve `rgba(255,179,92,.28)`, zemin `rgba(40,26,10,.4)`, metin `#ffc689`). Padding `7px 14px`, metin JetBrains Mono 10px `.2em`.
  - **Saat**: JetBrains Mono 28px `#eaf9ff`, `HH:MM:SS`, saniyede bir güncellenir. Altında Türkçe uzun tarih, büyük harf, 10px `.18em`.
  - **SİSTEM YAŞAM BELİRTİLERİ** (sol): 4 satır — İŞLEMCİ, BELLEK, GRAFİK, ÇEKİRDEK ISISI. Her satır: etiket (mono 10px `.16em`), değer (mono 13px `#5fe0ff`), 6px yükseklikte bar; dolgu `linear-gradient(90deg, rgba(95,224,255,.45), #5fe0ff)`, `box-shadow:0 0 12px rgba(95,224,255,.6)`, `transition:width .6s ease`.
  - **AĞ TRAFİĞİ** (sol): 28 çubuk, 76px yükseklik, 3px gap, dolgu `linear-gradient(180deg,#5fe0ff,rgba(95,224,255,.12))`, `transition:height .45s ease`. Altında ↓ MB/s, ↑ MB/s, PING ms.
  - **HAVA · İSTANBUL** (sol): 44px mono sıcaklık + sağda üç satır meta.
  - **Enerji çekirdeği** (orta): kare oran (`aspect-ratio:1/1`, `max-height:430px`), iç içe merkezlenmiş katmanlar:
    1. %100 yumuşak radial hale (statik)
    2. Kesikli dış halka, genişlik `94–99%` (ses seviyesine bağlı), `jspin 44s`
    3. %82 halka, 2px `rgba(95,224,255,.55)`, sağ+alt kenar şeffaf, `jspinrev 18s`
    4. %70 ince tam halka `rgba(95,224,255,.35)`
    5. %66 halka, 3px, üst kenar `#7ff0ff`, `jspin 7s`
    6. Amber halka, genişlik `48–56%`, 2px `rgba(255,179,92,.55)`, sol kenar şeffaf, `jspinrev 11s`
    7. Hale: genişlik `52–82%`, alfa `0.16–0.50`
    8. Çekirdek küre: genişlik `34–50%`, `radial-gradient(circle,#fff 0%,#d8f7ff 22%,#5fe0ff 55%,#1b6f96 82%,#0a3c55 100%)`, 2px `rgba(200,246,255,.9)` çerçeve, `box-shadow:0 0 45–135px 10px rgba(95,224,255,.55), inset 0 0 40px rgba(255,255,255,.45)`
    9. Merkez metin: durum ("BEKLEMEDE" / "DİNLİYOR") mono 12px `.3em` `#04202e`; altında "LVL 000–100"
    10. Sol/sağ kenarda "SYNC 100%" ve "LAT {ping}ms" etiketleri
    Ses seviyesine bağlı tüm genişlik/glow geçişleri `transition:… .09s linear`.
  - **SESLİ KOMUT** paneli (orta): 56px yuvarlak mikrofon butonu (içinde 14×22px yuvarlatılmış çerçeve ikon), yanında 40 çubuklu dalga formu (`transition:height .12s linear`), altta sol kenarında 2px `#5fe0ff` bulunan transkript satırı (mono 12px).
  - **BRIEF ME** düğmesi (orta): tam genişlik, `padding:16px`, çerçeve `1px solid rgba(95,224,255,.55)`, zemin `linear-gradient(180deg, rgba(95,224,255,.16), rgba(95,224,255,.05))`. Metin Rajdhani 700, 19px, `.4em`, `#eaf9ff`; alt satır ipucu mono 9px. Hover: çerçeve `#7ff0ff`, zemin daha parlak, `box-shadow:0 0 30px rgba(95,224,255,.35)`.
  - **Hızlı komutlar** (orta): 4 kolonlu grid — ODAK MODU, BRİFİNG, YEDEKLE, KİLİTLE. Hover: çerçeve `#5fe0ff`, zemin `rgba(95,224,255,.12)`.
  - **BAĞLANTI DURUMLARI** (sağ): 5 satır — UYDU BAĞI/KİLİTLİ, YEREL AĞ/{ping}ms, BULUT ÇEKİRDEĞİ/SENKRON, BİYOMETRİK/DOĞRULANDI, DIŞ API AĞ GEÇİDİ/KISITLI. Her satırda 6px renkli nokta (yeşil `#6effc0`, camgöbeği `#5fe0ff`, amber `#ffb35c`) + glow. Başlık sağında "4/5 STABİL".
  - **BUGÜNÜN AJANDASI** (sağ): saat (mono 11px `#5fe0ff`, min 44px) + sol kenarında ince çizgi olan başlık/meta bloğu; 4 kayıt.
  - **DİKKAT GEREKTİREN** (sağ): amber kart (`1px solid rgba(255,179,92,.24)`, zemin `linear-gradient(180deg, rgba(44,30,12,.5), rgba(20,14,6,.4))`), "!" işareti + 2 uyarı satırı.
  - **SİSTEM KAYDI** (footer): son 3 log satırı, mono 10px, satır bazında renk.

## Interactions & Behavior
- **Saat**: 1000ms aralık, `HH:MM:SS`; tarih `tr-TR` uzun format, büyük harf.
- **Telemetri simülasyonu**: 1400ms aralık; cpu ±10 (8–92), ram ±5 (40–88), gpu ±14 (4–80), temp ±3 (38–72); ağ dizisi baştan kaydırılıp sona 10–95 arası yeni değer eklenir; down 2–10 MB/s, up 0.4–2.8 MB/s, ping 8–22ms.
- **Mikrofon açma**: mikrofon butonuna tıklanınca `getUserMedia({audio:{echoCancellation:true,noiseSuppression:true}})` istenir. Başarılıysa `AudioContext` + `AnalyserNode` (`fftSize:128`, `smoothingTimeConstant:0.72`) kurulur ve `requestAnimationFrame` döngüsünde `getByteFrequencyData` okunur:
  - 40 çubuk: bin indeksi `floor(i/40 * bins * 0.7)`, yükseklik `6 + 94 * v^0.85` (v = byte/255)
  - `level = min(1, ortalama(v) * 2.2)` — çekirdek boyutu, glow, hale ve halka genişliklerini sürer
  - İzin reddedilirse simülasyona düşer (120ms aralık, sinüs zarflı rastgele çubuklar) ve log'a amber uyarı yazılır.
- **Mikrofon kapatma**: rAF iptal, tracks stop, AudioContext close, transkript "Hazırım. Bir komut bekliyorum." ve level 0.05'e döner.
- **Transkript**: dinleme başlarken "Dinliyorum…"; gerçek mikrofon yoksa 2600ms sonra örnek komut metni gösterilir.
- **BRIEF ME**: transkripte günlük özet yazar, log'a yeşil "brifing derlendi" satırı ekler, düğme ipucu "BRİFİNG İLETİLDİ" olur.
- **Hızlı komutlar**: her biri transkripti kendi mesajına ayarlar ve log'a amber bir satır ekler.
- **Log**: her zaman son 3 satır; zaman damgası `tr-TR`, 24 saatlik.
- **Responsive**: 3 kolon minmax ile daralır; daha darda yatay kaydırma.
- **Animasyon süreleri**: jspin 6/7/44s, jspinrev 9/11/18s, jpulse 4.5s, jbreathe 3.4s, jscan 9s, jblink 2.4s.

## State Management
`now`, `cpu`, `ram`, `gpu`, `temp`, `net[28]`, `wave[40]`, `level` (0–1), `listening`, `transcript`, `down`, `up`, `ping`, `briefed`, `logs[]`.
Yan referanslar (state dışı): `stream`, `actx`, `analyser`, `freq`, `raf`, 3 interval id.
Veri çekme yok — tüm veriler sabit veya simülasyon. Gerçek entegrasyonda: sistem metrikleri, hava, takvim, bağlantı sağlığı uçları bu alanların yerine geçer.

## Design Tokens
**Renkler**
- Zemin derinlikleri: `#0b2740`, `#061424`, `#03070e`
- Panel zeminleri: `rgba(10,34,56,.62)` → `rgba(6,20,34,.5)` gradient; satır zemini `rgba(6,22,38,.45–.5)`
- Çerçeveler: `rgba(95,224,255,.12 / .14 / .16 / .18 / .2 / .22 / .25 / .35 / .55)`
- Birincil aksan: `#5fe0ff`; parlak: `#7ff0ff`, `#d8f7ff`, `#eaf9ff`, `#b9f2ff`
- Metin: `#cfeeff` (gövde), `#d6f1ff`, `#bfe8fa`, `rgba(160,215,240,.45–.75)` (meta)
- Başarı/aktif: `#6effc0`, `#9fe8d0`
- Uyarı: `#ffb35c`, `#ffc689`, `#ffddb5`
- Çekirdek koyu tonları: `#1b6f96`, `#0a3c55`, metin `#04202e`

**Boşluk**: 2, 3, 4, 5, 8, 9, 10, 12, 14, 16, 18, 22, 26px. Panel padding 16px, kolon gap 18px, sayfa padding 22/26/18px.

**Tipografi**: Rajdhani (300–700) — başlıklar/etiketler; JetBrains Mono (300–500) — veri/kod. Ölçek: 9, 10, 11, 12, 13, 14, 15, 19, 26, 28, 44px. Letter-spacing: .06em, .1em, .12em, .14em, .16em, .18em, .2em, .22em, .24em, .26em, .28em, .3em, .4em, .42em.

**Köşe**: neredeyse tamamen 0 (keskin HUD); yalnızca yuvarlak öğelerde `border-radius:50%`, dalga çubuklarında 1px, mikrofon ikonunda 7px.

**Gölge**: `0 0 8px 2px` (durum noktaları), `0 0 12px` (bar), `0 0 14px 4px` (logo noktası), `0 0 18–30px` (halkalar/butonlar), `0 0 45–135px 10px` (çekirdek), `inset 0 0 40px rgba(255,255,255,.45)`.

## Assets
Görsel/ikon dosyası yok. Tüm grafikler CSS ile üretilir (halkalar, gradientler, grid dokusu). Yazı tipleri Google Fonts'tan: Rajdhani, JetBrains Mono. Hedef kod tabanında yerel font barındırma tercih ediliyorsa bu iki aile self-host edilebilir.

## Files
- `Jarvis Control Panel.dc.html` — tüm tasarım: şablon (markup + inline stiller) ve altında `class Component` içinde durum/zamanlayıcı/ses mantığı.
