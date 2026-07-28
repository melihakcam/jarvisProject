"""JARVIS - Gercek hava durumu.

Konum IP adresinden bulunur, hava verisi Open-Meteo'dan alinir. Her ikisi de
ucretsiz ve API anahtari gerektirmez. Veri 10 dakika onbelleklenir; internet
yoksa panel son bilinen degeri "eski veri" isaretiyle gosterir.

Tek basina test:
    python jarvis/weather.py
"""
import json
import threading
import time
import urllib.parse
import urllib.request

_ONBELLEK_SURESI = 600           # 10 dakika
_KONUM_ONBELLEK_SURESI = 3600    # 1 saat

_kilit = threading.Lock()
_onbellek = {"zaman": 0, "veri": None}
_konum = {"zaman": 0, "veri": None}

# Open-Meteo WMO hava kodlari -> Turkce aciklama
_KODLAR = {
    0: "Açık", 1: "Az Bulutlu", 2: "Parçalı Bulutlu", 3: "Kapalı",
    45: "Sisli", 48: "Kırağılı Sis",
    51: "Hafif Çisenti", 53: "Çisenti", 55: "Yoğun Çisenti",
    56: "Donan Çisenti", 57: "Yoğun Donan Çisenti",
    61: "Hafif Yağmur", 63: "Yağmurlu", 65: "Şiddetli Yağmur",
    66: "Donan Yağmur", 67: "Şiddetli Donan Yağmur",
    71: "Hafif Kar", 73: "Karlı", 75: "Yoğun Kar", 77: "Kar Taneleri",
    80: "Sağanak", 81: "Kuvvetli Sağanak", 82: "Şiddetli Sağanak",
    85: "Kar Sağanağı", 86: "Yoğun Kar Sağanağı",
    95: "Gök Gürültülü", 96: "Dolulu Fırtına", 99: "Şiddetli Dolulu Fırtına",
}


def _getir(url: str, zaman_asimi: int = 6):
    istek = urllib.request.Request(url, headers={"User-Agent": "JARVIS/1.0"})
    with urllib.request.urlopen(istek, timeout=zaman_asimi) as yanit:
        return json.loads(yanit.read().decode("utf-8"))


def konum():
    """IP adresinden gercek konum. Basarisiz olursa None."""
    with _kilit:
        if _konum["veri"] and time.time() - _konum["zaman"] < _KONUM_ONBELLEK_SURESI:
            return _konum["veri"]
    for url, esle in (
        ("http://ip-api.com/json/?fields=status,city,lat,lon",
         lambda d: (d.get("lat"), d.get("lon"), d.get("city")) if d.get("status") == "success" else None),
        ("https://ipapi.co/json/",
         lambda d: (d.get("latitude"), d.get("longitude"), d.get("city"))),
    ):
        try:
            v = esle(_getir(url))
            if v and v[0] is not None and v[1] is not None:
                veri = {"lat": float(v[0]), "lon": float(v[1]), "city": (v[2] or "").upper()}
                with _kilit:
                    _konum["veri"], _konum["zaman"] = veri, time.time()
                return veri
        except Exception:
            continue
    return None


def _yon(derece):
    yonler = ["K", "KD", "D", "GD", "G", "GB", "B", "KB"]
    return yonler[int((derece % 360) / 45 + 0.5) % 8]


def hava(sehir_lat=None, sehir_lon=None):
    """Gercek hava durumu. Basarisiz olursa son bilinen veriyi 'stale' ile doner."""
    with _kilit:
        if _onbellek["veri"] and time.time() - _onbellek["zaman"] < _ONBELLEK_SURESI:
            return _onbellek["veri"]

    k = None
    if sehir_lat is not None and sehir_lon is not None:
        k = {"lat": sehir_lat, "lon": sehir_lon, "city": ""}
    else:
        k = konum()

    if k is None:
        with _kilit:
            eski = _onbellek["veri"]
        if eski:
            eski = dict(eski, stale=True)
            return eski
        return {"ok": False, "city": "KONUM YOK", "temp": "--°",
                "desc": "Veri alınamıyor", "meta1": "İnternet bağlantısı gerekli",
                "meta2": "", "stale": False}

    url = ("https://api.open-meteo.com/v1/forecast"
           f"?latitude={k['lat']}&longitude={k['lon']}"
           "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
           "is_day,weather_code,wind_speed_10m,wind_direction_10m"
           "&daily=uv_index_max,temperature_2m_max,temperature_2m_min"
           "&timezone=auto&forecast_days=1")
    try:
        d = _getir(url)
        c = d["current"]
        gun = d.get("daily", {})
        uv = (gun.get("uv_index_max") or [None])[0]
        enyuksek = (gun.get("temperature_2m_max") or [None])[0]
        endusuk = (gun.get("temperature_2m_min") or [None])[0]
        kod = int(c.get("weather_code", 0))
        veri = {
            "ok": True,
            "city": k["city"] or "KONUM",
            "temp": f"{round(c['temperature_2m'])}°",
            "desc": _KODLAR.get(kod, "Bilinmiyor"),
            "meta1": (f"NEM %{round(c['relative_humidity_2m'])} · "
                      f"RÜZGAR {round(c['wind_speed_10m'])} km/s "
                      f"{_yon(c.get('wind_direction_10m', 0))}"),
            "meta2": (f"HİSSEDİLEN {round(c['apparent_temperature'])}°"
                      + (f" · UV {round(uv)}" if uv is not None else "")
                      + (f" · {round(endusuk)}°/{round(enyuksek)}°"
                         if endusuk is not None and enyuksek is not None else "")),
            "raw": {"temp": c["temperature_2m"], "feels": c["apparent_temperature"],
                    "code": kod, "min": endusuk, "max": enyuksek},
            "stale": False,
        }
        with _kilit:
            _onbellek["veri"], _onbellek["zaman"] = veri, time.time()
        return veri
    except Exception:
        with _kilit:
            eski = _onbellek["veri"]
        if eski:
            return dict(eski, stale=True)
        return {"ok": False, "city": k["city"] or "KONUM", "temp": "--°",
                "desc": "Veri alınamıyor", "meta1": "Hava servisine ulaşılamadı",
                "meta2": "", "stale": False}


def ozet_metin():
    """Brifing icin sesli okunabilir hava ozeti."""
    h = hava()
    if not h.get("ok"):
        return "Hava durumu bilgisine şu an ulaşamıyorum efendim."
    ham = h.get("raw", {})
    metin = (f"{h['city'].title()} için hava {h['desc'].lower()}, "
             f"sıcaklık {h['temp'].rstrip('°')} derece")
    if ham.get("min") is not None and ham.get("max") is not None:
        metin += (f", gün içinde {round(ham['min'])} ile {round(ham['max'])} "
                  f"derece arasında seyredecek")
    return metin + "."


if __name__ == "__main__":
    print("Konum:", konum())
    h = hava()
    for anahtar in ("city", "temp", "desc", "meta1", "meta2", "stale"):
        print(f"  {anahtar}: {h.get(anahtar)}")
    print("Ozet:", ozet_metin())
