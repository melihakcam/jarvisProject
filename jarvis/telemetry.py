"""JARVIS - Gercek sistem telemetrisi.

Panelin sol sutunundaki "SISTEM YASAM BELIRTILERI" ve "AG TRAFIGI" kartlari ile
sag sutundaki "BAGLANTI DURUMLARI" / "DIKKAT GEREKTIREN" kartlarini besler.
Tum degerler gercektir; okunamayan bir olcum varsa uydurulmaz, listeden dusurulur.

Tek basina test:
    python jarvis/telemetry.py
"""
import os
import shutil
import socket
import subprocess
import threading
import time

import psutil

try:
    from jarvis import config
except ImportError:
    import config

_GIZLI = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Proje hangi surucudeyse depolama olcumu onun uzerinden yapilir (D:).
PROJE_SURUCUSU = os.path.splitdrive(str(config.PROJE_KOKU))[0] + os.sep


# --------------------------------------------------------------------------
# Arka planda ornekleme gerektiren olcumler (yavas olduklari icin ayri thread)
# --------------------------------------------------------------------------
# CPU ve ag hizi *sabit araliklarla* ornekleyici thread'de olculur. Bunlar
# "son cagridan bu yana" mantigiyla calisir; birden fazla istemci (panel + baska
# bir sekme) ayni anda sorarsa dogrudan olcum sifira duser. Onbellekten okumak
# kac istemci baglanirsa baglansin dogru deger verir.
_ornek = {
    "cpu": 0.0,         # yuzde
    "gpu": None,        # yuzde ya da None (okunamiyorsa)
    "ping": None,       # ms ya da None (internet yok)
    "gateway": None,    # yerel ag gecikmesi (ms) ya da None
    "internet": False,
    "olculdu": False,   # ilk ag olcumu tamamlandi mi (bilinmiyor != yok)
    "down": 0.0,        # MB/s
    "up": 0.0,          # MB/s
    "bars": [],         # cubuk grafik gecmisi
}
_ornek_kilidi = threading.Lock()


def _ps(komut: str, zaman_asimi: int = 12) -> str:
    """Kisa bir PowerShell komutu calistirip ciktisini dondurur."""
    sonuc = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", komut],
        capture_output=True, text=True, timeout=zaman_asimi,
        creationflags=_GIZLI,
    )
    return (sonuc.stdout or "").strip()


def _gpu_olc():
    """Windows performans sayaclarindan gercek GPU kullanimi (%)."""
    try:
        cikti = _ps(
            "$s=(Get-Counter '\\GPU Engine(*engtype_3D)\\Utilization Percentage'"
            " -ErrorAction Stop).CounterSamples | Measure-Object CookedValue -Sum;"
            " [math]::Round($s.Sum,1)"
        )
        return max(0.0, min(100.0, float(cikti.replace(",", "."))))
    except Exception:
        return None


def _ping_olc(hedef: str):
    """Gercek ICMP ping (ms). Ulasilmazsa None."""
    try:
        sonuc = subprocess.run(["ping", "-n", "1", "-w", "1500", hedef],
                               capture_output=True, text=True, timeout=6,
                               creationflags=_GIZLI)
        if sonuc.returncode != 0:
            return None
        for parca in (sonuc.stdout or "").replace("=", " ").replace("<", " ").split():
            if parca.endswith("ms"):
                try:
                    return int(float(parca[:-2]))
                except ValueError:
                    continue
    except Exception:
        pass
    return None


def _tcp_gecikme(host: str, port: int = 443):
    """ICMP engelli aglarda gecikmeyi TCP el sikismasiyla olcer (ms)."""
    baslangic = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=2):
            return int((time.perf_counter() - baslangic) * 1000)
    except Exception:
        return None


# Bazi aglar belirli IP'lere ICMP'yi engeller; sirayla denenir.
_PING_HEDEFLERI = ("8.8.8.8", "1.1.1.1", "9.9.9.9")


def _internet_gecikmesi():
    """Internet gecikmesi (ms). Once ICMP, olmazsa TCP ile olculur."""
    for hedef in _PING_HEDEFLERI:
        ms = _ping_olc(hedef)
        if ms is not None:
            return ms
    for host in ("cloudflare.com", "google.com"):
        ms = _tcp_gecikme(host)
        if ms is not None:
            return ms
    return None


def _ag_gecidi():
    """Varsayilan ag gecidinin IP adresi (yerel ag gecikmesi olcumu icin)."""
    try:
        cikti = _ps("(Get-NetRoute -DestinationPrefix '0.0.0.0/0'"
                    " -ErrorAction Stop | Sort-Object RouteMetric |"
                    " Select-Object -First 1).NextHop")
        cikti = cikti.strip()
        return cikti or None
    except Exception:
        return None


_gecit_ip = None


def _hizli_ornekleyici():
    """CPU ve ag hizini sabit 2 saniyelik araliklarla olcer."""
    while True:
        cpu = psutil.cpu_percent(interval=2)   # blokli olcum: tam 2 sn'lik ortalama
        indir, yukle = _ag_hizi()
        with _ornek_kilidi:
            _ornek["cpu"] = cpu
            _ornek["down"] = indir
            _ornek["up"] = yukle
            _ornek["bars"] = list(_gecmisi_guncelle(indir, yukle))


def _yavas_ornekleyici():
    """GPU ve ag gecikmesi gibi pahali olcumleri arka planda tazeler."""
    global _gecit_ip
    _gecit_ip = _ag_gecidi()
    while True:
        gpu = _gpu_olc()
        ping = _internet_gecikmesi()
        gecit = _ping_olc(_gecit_ip) if _gecit_ip else None
        with _ornek_kilidi:
            _ornek["gpu"] = gpu
            _ornek["ping"] = ping
            _ornek["gateway"] = gecit
            _ornek["internet"] = ping is not None
            _ornek["olculdu"] = True
        time.sleep(4)


_ornekleyici_basladi = False


def baslat():
    """Arka plan ornekleyicilerini bir kez baslatir."""
    global _ornekleyici_basladi
    if _ornekleyici_basladi:
        return
    _ornekleyici_basladi = True
    _ag_hizi()                                 # bayt sayaclarinin baslangicini al
    threading.Thread(target=_hizli_ornekleyici, daemon=True).start()
    threading.Thread(target=_yavas_ornekleyici, daemon=True).start()


# --------------------------------------------------------------------------
# Ag trafigi (gercek bayt sayaclarindan turetilir)
# --------------------------------------------------------------------------
_son_sayac = None
_son_zaman = None
_gecmis = []            # panelin cubuk grafigi icin son 28 olcum (%)
_GECMIS_UZUNLUK = 28


def _ag_hizi():
    """psutil bayt sayaclarindan gercek indirme/yukleme hizi (MB/s)."""
    global _son_sayac, _son_zaman
    simdi = time.time()
    sayac = psutil.net_io_counters()
    if _son_sayac is None or _son_zaman is None:
        _son_sayac, _son_zaman = sayac, simdi
        return 0.0, 0.0
    dt = max(0.001, simdi - _son_zaman)
    indir = max(0, sayac.bytes_recv - _son_sayac.bytes_recv) / dt / (1024 * 1024)
    yukle = max(0, sayac.bytes_sent - _son_sayac.bytes_sent) / dt / (1024 * 1024)
    _son_sayac, _son_zaman = sayac, simdi
    return indir, yukle


def _gecmisi_guncelle(indir, yukle):
    """Cubuk grafigi icin trafigi 0-100 araligina olcekler (log olcek: hem
    kilobaytlik hem onlarca megabaytlik trafik ayni grafikte gorunsun)."""
    import math
    toplam = indir + yukle
    yuzde = 0 if toplam <= 0 else min(100, int(100 * math.log10(1 + toplam * 40) / math.log10(1 + 20 * 40)))
    _gecmis.append(max(2, yuzde))
    while len(_gecmis) > _GECMIS_UZUNLUK:
        _gecmis.pop(0)
    return _gecmis


# --------------------------------------------------------------------------
# Yasam belirtileri
# --------------------------------------------------------------------------
def _sicaklik():
    """CPU sicakligi (°C). Windows'ta yonetici yetkisi olmadan cogunlukla
    okunamaz; okunamiyorsa None doner ve panelde gosterilmez."""
    try:
        okuma = getattr(psutil, "sensors_temperatures", lambda: {})()
        for girdiler in (okuma or {}).values():
            for g in girdiler:
                if g.current and g.current > 0:
                    return round(g.current)
    except Exception:
        pass
    return None


def vitals():
    """Panelin 'SISTEM YASAM BELIRTILERI' kartindaki gercek olcumler."""
    with _ornek_kilidi:
        gpu = _ornek["gpu"]
        islemci = round(_ornek["cpu"])

    bellek = psutil.virtual_memory()
    disk = psutil.disk_usage(PROJE_SURUCUSU)
    liste = [
        {"key": "cpu", "label": "İŞLEMCİ", "value": islemci, "unit": "%", "pct": islemci,
         "detail": f"{psutil.cpu_count(logical=True)} çekirdek"},
        {"key": "ram", "label": "BELLEK", "value": round(bellek.percent),
         "unit": "%", "pct": round(bellek.percent),
         "detail": f"{bellek.used/1024**3:.1f}/{bellek.total/1024**3:.0f} GB"},
    ]
    if gpu is not None:
        liste.append({"key": "gpu", "label": "GRAFİK", "value": round(gpu),
                      "unit": "%", "pct": round(gpu)})
    liste.append({
        "key": "disk", "label": f"DEPOLAMA {PROJE_SURUCUSU[0]}:",
        "value": round(disk.percent), "unit": "%", "pct": round(disk.percent),
        "detail": f"{disk.free/1024**3:.0f} GB boş",
    })

    sic = _sicaklik()
    if sic is not None:
        liste.append({"key": "temp", "label": "ÇEKİRDEK ISISI", "value": sic,
                      "unit": "°C", "pct": min(100, round(sic / 90 * 100))})

    pil = psutil.sensors_battery()
    if pil is not None:
        liste.append({
            "key": "batt", "label": "BATARYA", "value": round(pil.percent),
            "unit": "%", "pct": round(pil.percent),
            "detail": "şarjda" if pil.power_plugged else "pilde",
        })
    return liste


def _hiz_yazi(mb_sn: float) -> str:
    """Kucuk trafikte MB/s hep 0.0 gorunmesin diye birim otomatik secilir."""
    if mb_sn >= 1:
        return f"{mb_sn:.1f} MB/s"
    if mb_sn >= 0.001:
        return f"{mb_sn * 1024:.0f} KB/s"
    return "0 KB/s"


def ag():
    """Gercek ag trafigi ve gecikme (ornekleyici thread'in son olcumu)."""
    with _ornek_kilidi:
        ping, indir, yukle = _ornek["ping"], _ornek["down"], _ornek["up"]
        bars = list(_ornek["bars"])
    w = wifi_bilgisi()
    if w.get("ssid"):
        detay = " · ".join(p for p in (
            w["ssid"],
            f"sinyal {w['signal']}" if w.get("signal") else "",
            w.get("band", ""),
            f"{w['rate']} Mbps" if w.get("rate") else "",
        ) if p)
    else:
        detay = "Kablolu bağlantı"
    return {"down": _hiz_yazi(indir), "up": _hiz_yazi(yukle),
            "ping": ping, "bars": bars, "detail": detay, "wifi": w}


# --------------------------------------------------------------------------
# Baglanti durumlari (hepsi gercek kontrol)
# --------------------------------------------------------------------------
YESIL = ("#6effc0", "rgba(110,255,192,.6)")
MAVI = ("#5fe0ff", "rgba(95,224,255,.6)")
AMBER = ("#ffb35c", "rgba(255,179,92,.55)")
KIRMIZI = ("#ff7a7a", "rgba(255,122,122,.55)")


def _satir(ad, durum, renk):
    return {"name": ad, "status": durum, "dot": renk[0], "glow": renk[1],
            "ok": renk in (YESIL, MAVI)}


_mikrofon_var = None


def _mikrofon_kontrol():
    global _mikrofon_var
    if _mikrofon_var is None:
        try:
            import sounddevice as sd
            _mikrofon_var = any(c["max_input_channels"] > 0 for c in sd.query_devices())
        except Exception:
            _mikrofon_var = False
    return _mikrofon_var


def baglantilar(stt_hazir: bool = False):
    """Panelin 'BAGLANTI DURUMLARI' listesi - her satir gercek bir kontrol."""
    with _ornek_kilidi:
        ping, gecit, net = _ornek["ping"], _ornek["gateway"], _ornek["internet"]
        olculdu = _ornek["olculdu"]

    if not olculdu:
        internet_satiri = _satir("İNTERNET", "ÖLÇÜLÜYOR", AMBER)
    elif net:
        internet_satiri = _satir("İNTERNET", f"{ping}ms", YESIL)
    else:
        internet_satiri = _satir("İNTERNET", "YOK", KIRMIZI)

    # Bagli olunan agin gercek adi satirda gorunur (kablolu ise "KABLOLU")
    ag_adi = _wifi_adi()
    satirlar = [
        internet_satiri,
        _satir(f"AĞ · {ag_adi.upper()}" if ag_adi else "YEREL AĞ (KABLOLU)",
               f"{gecit}ms" if gecit is not None else ("BAĞLI" if ag_adi else "YOK"),
               YESIL if gecit is not None else AMBER),
        _satir("PANEL SUNUCUSU", "ÇEVRİMİÇİ", MAVI),
        _satir("SES TANIMA", "HAZIR" if stt_hazir else "YÜKLENİYOR",
               MAVI if stt_hazir else AMBER),
        _satir("MİKROFON", "ALGILANDI" if _mikrofon_kontrol() else "YOK",
               MAVI if _mikrofon_kontrol() else KIRMIZI),
        _satir("BEYİN · CLAUDE", "BAĞLI" if beyin_var() else "KURULU DEĞİL",
               YESIL if beyin_var() else AMBER),
    ]
    stabil = sum(1 for s in satirlar if s["ok"])
    return satirlar, f"{stabil}/{len(satirlar)} STABİL"


_beyin_onbellek = {"zaman": 0, "var": False}


def beyin_var() -> bool:
    """Claude Code CLI kurulu mu (30 saniyede bir tazelenir)."""
    if time.time() - _beyin_onbellek["zaman"] > 30:
        _beyin_onbellek["var"] = shutil.which(config.CLAUDE_KOMUTU) is not None
        _beyin_onbellek["zaman"] = time.time()
    return _beyin_onbellek["var"]


_wifi_onbellek = {"zaman": 0, "veri": {}}

# netsh ciktisi Windows'un diline gore degisir; her alanin karsiliklari:
_WIFI_ALANLARI = {
    "ssid": ("ssid", "ssıd"),
    "signal": ("signal", "sinyal"),
    "band": ("band", "bant"),
    "radio": ("radio type", "radyo türü", "radyo turu"),
    "auth": ("authentication", "kimlik doğrulama", "kimlik dogrulama"),
    "rate": ("receive rate (mbps)", "alma hızı (mbps)", "alma hizi (mbps)"),
    "state": ("state", "durum"),
}


def wifi_bilgisi():
    """Bagli olunan Wi-Fi aginin gercek bilgileri (60 saniyede bir tazelenir).
    Kablolu baglantida ya da Wi-Fi kapaliysa bos sozluk doner."""
    if time.time() - _wifi_onbellek["zaman"] <= 60:
        return _wifi_onbellek["veri"]

    _wifi_onbellek["zaman"] = time.time()
    veri = {}
    try:
        cikti = subprocess.run(["netsh", "wlan", "show", "interfaces"],
                               capture_output=True, text=True, timeout=6,
                               errors="replace", creationflags=_GIZLI).stdout or ""
        for satir in cikti.splitlines():
            if ":" not in satir:
                continue
            etiket, _, deger = satir.partition(":")
            etiket, deger = etiket.strip().lower(), deger.strip()
            # "SSID" ile "BSSID"i karistirmamak icin tam eslesme aranir
            for anahtar, adlar in _WIFI_ALANLARI.items():
                if etiket in adlar and anahtar not in veri:
                    veri[anahtar] = deger
        # baglanti kopmussa SSID eski deger olarak kalabilir
        if veri.get("state", "").lower() not in ("connected", "bağlı", "bagli"):
            veri.pop("ssid", None)
    except Exception:
        veri = {}
    _wifi_onbellek["veri"] = veri
    return veri


def _wifi_adi():
    return wifi_bilgisi().get("ssid", "")


# --------------------------------------------------------------------------
# Dikkat gerektiren (gercek durumlardan uretilir)
# --------------------------------------------------------------------------
def uyarilar(ajanda_yaklasan=None):
    """Gercek sistem durumundan turetilmis uyari listesi."""
    liste = []

    for surucu in _surucular():
        kullanim = surucu["pct"]
        if kullanim >= 95:
            liste.append({"text": f"{surucu['ad']} sürücüsü %{kullanim} dolu — "
                                  f"yalnızca {surucu['bos']:.1f} GB boş kaldı.",
                          "level": "kritik"})
        elif kullanim >= 88:
            liste.append({"text": f"{surucu['ad']} sürücüsü %{kullanim} dolu — "
                                  f"{surucu['bos']:.0f} GB boş.", "level": "uyari"})

    bellek = psutil.virtual_memory()
    if bellek.percent >= 88:
        liste.append({"text": f"Bellek kullanımı %{round(bellek.percent)} — "
                              f"uygulama kapatmayı düşünün.", "level": "uyari"})

    pil = psutil.sensors_battery()
    if pil is not None and not pil.power_plugged and pil.percent <= 25:
        kalan = ""
        if pil.secsleft and pil.secsleft > 0:
            kalan = f" — yaklaşık {pil.secsleft // 60} dakika kaldı"
        liste.append({"text": f"Batarya %{round(pil.percent)}{kalan}. Şarja takın.",
                      "level": "uyari"})

    with _ornek_kilidi:
        net, olculdu = _ornek["internet"], _ornek["olculdu"]
    if olculdu and not net:
        liste.append({"text": "İnternet bağlantısı yok — beyin ve hava durumu "
                              "devre dışı.", "level": "kritik"})

    if not beyin_var():
        liste.append({"text": "Claude Code kurulu değil — serbest sorular "
                              "yanıtlanamıyor.", "level": "uyari"})

    for iş in (ajanda_yaklasan or []):
        liste.append({"text": f"{iş['time']} · {iş['title']} — {iş['kalan']}",
                      "level": "ajanda"})

    if not liste:
        liste.append({"text": "Dikkat gerektiren bir durum yok efendim.",
                      "level": "ok"})
    return liste


def _surucular():
    """Sabit disklerin gercek doluluk oranlari."""
    sonuc = []
    for b in psutil.disk_partitions(all=False):
        if "cdrom" in b.opts or not b.fstype:
            continue
        try:
            k = psutil.disk_usage(b.mountpoint)
        except (PermissionError, OSError):
            continue
        sonuc.append({"ad": b.device.rstrip("\\").rstrip(":"), "pct": round(k.percent),
                      "bos": k.free / 1024 ** 3, "toplam": k.total / 1024 ** 3})
    return sonuc


def ozet_metin():
    """Brifing icin sistem durumunun sesli okunabilir ozeti."""
    v = {x["key"]: x for x in vitals()}
    parcalar = [f"İşlemci yüzde {v['cpu']['value']}, bellek yüzde {v['ram']['value']}"]
    if "disk" in v:
        parcalar.append(f"{PROJE_SURUCUSU[0]} sürücüsünde {v['disk']['detail']} alan var")
    if "batt" in v:
        parcalar.append(f"batarya yüzde {v['batt']['value']} ve {v['batt']['detail']}")
    with _ornek_kilidi:
        ping, olculdu = _ornek["ping"], _ornek["olculdu"]
    if ping is not None:
        parcalar.append(f"ağ gecikmesi {ping} milisaniye")
    elif olculdu:
        parcalar.append("internet bağlantısı görünmüyor")
    return ", ".join(parcalar) + "."


def bilgisayar_adi():
    try:
        return socket.gethostname()
    except Exception:
        return "bilinmeyen"


if __name__ == "__main__":
    baslat()
    time.sleep(5)
    print("Yasam belirtileri:")
    for s in vitals():
        print(f"  {s['label']}: {s['value']}{s['unit']} {s.get('detail','')}")
    print("Ag:", ag())
    sat, ozet = baglantilar(stt_hazir=True)
    print("Baglantilar:", ozet)
    for s in sat:
        print(f"  {s['name']}: {s['status']}")
    print("Uyarilar:")
    for u in uyarilar():
        print("  -", u["text"])
    print("Ozet:", ozet_metin())
