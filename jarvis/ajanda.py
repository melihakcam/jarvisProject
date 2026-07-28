"""JARVIS - Ajanda ve hatirlaticilar (kalici kayit).

Kayitlar D: surucusundeki  data/ajanda.json  dosyasinda tutulur. Panelden veya
sesli komutla eklenir, zamani gelince JARVIS sesli olarak hatirlatir.

    "bana 15:00'te toplanti hatirlat"      -> bugun 15:00
    "yarin 09:30 dis randevusu hatirlat"   -> yarin 09:30
    "20 dakika sonra cayi al hatirlat"     -> simdi + 20 dk

Tek basina test:
    python jarvis/ajanda.py
"""
import datetime
import json
import re
import threading
import unicodedata
import uuid

try:
    from jarvis import config
except ImportError:
    import config

VERI_KLASORU = config.PROJE_KOKU / "data"
AJANDA_DOSYASI = VERI_KLASORU / "ajanda.json"

_kilit = threading.Lock()


def _yukle():
    try:
        with open(AJANDA_DOSYASI, "r", encoding="utf-8") as f:
            veri = json.load(f)
        return veri if isinstance(veri, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _kaydet(kayitlar):
    VERI_KLASORU.mkdir(parents=True, exist_ok=True)
    gecici = AJANDA_DOSYASI.with_suffix(".tmp")
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(kayitlar, f, ensure_ascii=False, indent=2)
    gecici.replace(AJANDA_DOSYASI)


def _bugun():
    return datetime.date.today().isoformat()


def liste(tarih=None):
    """Verilen gunun (varsayilan bugun) kayitlarini saate gore sirali dondurur."""
    hedef = tarih or _bugun()
    with _kilit:
        kayitlar = [k for k in _yukle() if k.get("date") == hedef]
    return sorted(kayitlar, key=lambda k: k.get("time", "99:99"))


def tumu():
    with _kilit:
        return sorted(_yukle(), key=lambda k: (k.get("date", ""), k.get("time", "")))


def ekle(saat: str, baslik: str, meta: str = "HATIRLATICI", tarih=None):
    """Yeni bir kayit ekler ve eklenen kaydi dondurur."""
    kayit = {
        "id": uuid.uuid4().hex[:8],
        "date": tarih or _bugun(),
        "time": _saat_duzelt(saat),
        "title": baslik.strip(),
        "meta": meta,
        "notified": False,
        "created": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    with _kilit:
        kayitlar = _yukle()
        kayitlar.append(kayit)
        _kaydet(kayitlar)
    return kayit


def sil(kayit_id: str) -> bool:
    with _kilit:
        kayitlar = _yukle()
        kalan = [k for k in kayitlar if k.get("id") != kayit_id]
        if len(kalan) == len(kayitlar):
            return False
        _kaydet(kalan)
    return True


def _isaretle(kayit_id: str, alan: str, deger=True):
    with _kilit:
        kayitlar = _yukle()
        for k in kayitlar:
            if k.get("id") == kayit_id:
                k[alan] = deger
                _kaydet(kayitlar)
                return True
    return False


def tamamla(kayit_id: str) -> bool:
    return _isaretle(kayit_id, "done", True)


def _saat_duzelt(saat: str) -> str:
    saat = (saat or "").strip().replace(".", ":")
    parcalar = saat.split(":")
    try:
        s = int(parcalar[0])
        d = int(parcalar[1]) if len(parcalar) > 1 else 0
    except (ValueError, IndexError):
        return "00:00"
    return f"{max(0, min(23, s)):02d}:{max(0, min(59, d)):02d}"


def _zaman(kayit):
    """Kaydin datetime karsiligi."""
    try:
        return datetime.datetime.fromisoformat(f"{kayit['date']}T{kayit['time']}:00")
    except (ValueError, KeyError):
        return None


def yaklasan(dakika: int = 60):
    """Onumuzdeki N dakika icinde baslayacak kayitlar (panel uyarilari icin)."""
    simdi = datetime.datetime.now()
    sonuc = []
    for k in liste():
        if k.get("done"):
            continue
        z = _zaman(k)
        if z is None:
            continue
        fark = (z - simdi).total_seconds() / 60
        if 0 <= fark <= dakika:
            sonuc.append(dict(k, kalan=(f"{round(fark)} dakika içinde"
                                        if fark >= 1 else "şimdi")))
    return sonuc


def zamani_gelenler():
    """Saati gelmis ve henuz hatirlatilmamis kayitlari dondurur; ayni kaydin
    ikinci kez hatirlatilmamasi icin isaretler."""
    simdi = datetime.datetime.now()
    tetiklenen = []
    with _kilit:
        kayitlar = _yukle()
        degisti = False
        for k in kayitlar:
            if k.get("notified") or k.get("done") or k.get("date") != _bugun():
                continue
            try:
                z = datetime.datetime.fromisoformat(f"{k['date']}T{k['time']}:00")
            except (ValueError, KeyError):
                continue
            gecen = (simdi - z).total_seconds()
            if 0 <= gecen <= 300:          # saati gecmis ama 5 dakikadan taze
                k["notified"] = True
                degisti = True
                tetiklenen.append(dict(k))
            elif gecen > 300:              # cok eski: sessizce kapat
                k["notified"] = True
                degisti = True
        if degisti:
            _kaydet(kayitlar)
    return tetiklenen


# --------------------------------------------------------------------------
# Sesli komuttan hatirlatici olusturma
# --------------------------------------------------------------------------
def _sadelestir(metin: str) -> str:
    s = (metin or "").lower().replace("ı", "i")
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


_SAAT_KALIBI = re.compile(r"\b(\d{1,2})[:.](\d{2})\b")
_SAAT_TEK = re.compile(r"\b(?:saat\s+)?(\d{1,2})\s*(?:'?[dt]e|'?[dt]a)\b")
_SONRA_KALIBI = re.compile(r"\b(\d{1,3})\s*(dakika|dakka|saat)\s*sonra\b")


def komuttan_ekle(metin: str):
    """'... hatirlat' bicimindeki sesli komuttan kayit olusturur.
    Anlasilmazsa None doner (metin hatirlatici komutu degildir)."""
    ham = metin or ""
    t = _sadelestir(ham)
    if "hatirlat" not in t and "hatirlatici" not in t:
        return None

    simdi = datetime.datetime.now()
    tarih = simdi.date()
    zaman = None

    m = _SONRA_KALIBI.search(t)
    if m:
        miktar = int(m.group(1))
        delta = (datetime.timedelta(hours=miktar) if m.group(2) == "saat"
                 else datetime.timedelta(minutes=miktar))
        hedef = simdi + delta
        tarih, zaman = hedef.date(), hedef.strftime("%H:%M")
    else:
        m = _SAAT_KALIBI.search(t)
        if m:
            zaman = _saat_duzelt(f"{m.group(1)}:{m.group(2)}")
        else:
            m = _SAAT_TEK.search(t)
            if m:
                zaman = _saat_duzelt(f"{m.group(1)}:00")
        if "yarin" in t:
            tarih = simdi.date() + datetime.timedelta(days=1)

    if zaman is None:
        return {"ok": False,
                "answer": "Saati anlayamadım efendim. Örneğin "
                          "'saat on beş sıfır sıfırda toplantı hatırlat' diyebilirsiniz."}

    # Basligi ayikla: zaman ifadelerini ve komut kelimelerini temizle
    baslik = ham
    # Saat ifadesi, pesindeki bulunma ekiyle birlikte temizlenir ("15:30'da")
    for desen in (r"\b\d{1,2}[:.]\d{2}\s*['’]?\s*(?:da|de|ta|te)?\b",
                  r"\b\d{1,3}\s*(dakika|dakka|saat)\s*sonra\b",
                  r"\bsaat\b", r"\bhatırlatıcı\b", r"\bhatirlatici\b",
                  r"\bhatırlat\b", r"\bhatirlat\b", r"\bbana\b", r"\byarın\b",
                  r"\byarin\b", r"\bbugün\b", r"\bbugun\b", r"\bjarvis\b",
                  r"\bekle\b", r"\bkur\b", r"\b\d{1,2}\s*'?[dtDT][eaEA]\b"):
        baslik = re.sub(desen, " ", baslik, flags=re.IGNORECASE)
    baslik = re.sub(r"^\s*['’]?\s*(?:da|de|ta|te)\b", " ", baslik, flags=re.IGNORECASE)
    baslik = " ".join(baslik.split()).strip(" ,.-'’")
    if not baslik:
        baslik = "Hatırlatıcı"
    baslik = baslik[0].upper() + baslik[1:]

    kayit = ekle(zaman, baslik, meta="SESLİ HATIRLATICI",
                 tarih=tarih.isoformat())
    ne_zaman = "yarın" if tarih != simdi.date() else "bugün"
    return {"ok": True, "kayit": kayit,
            "answer": f"Tamamdır efendim, {ne_zaman} saat {zaman} için "
                      f"{baslik} hatırlatıcısını kurdum."}


def ozet_metin():
    """Brifing icin sesli okunabilir ajanda ozeti."""
    kayitlar = [k for k in liste() if not k.get("done")]
    if not kayitlar:
        return "Bugün için ajandanızda kayıt yok efendim."
    simdi = datetime.datetime.now().strftime("%H:%M")
    kalan = [k for k in kayitlar if k["time"] >= simdi]
    if not kalan:
        return f"Bugünkü {len(kayitlar)} maddenin tamamı geride kaldı efendim."
    parcalar = [f"saat {k['time']} {k['title']}" for k in kalan[:4]]
    bas = f"Günün geri kalanında {len(kalan)} madde var efendim: "
    return bas + ", ".join(parcalar) + "."


if __name__ == "__main__":
    print("Dosya:", AJANDA_DOSYASI)
    print("Bugün:", liste())
    for ornek in ("bana 15:30'da toplantı hatırlat",
                  "yarın 09:00 diş randevusu hatırlat",
                  "20 dakika sonra çayı al hatırlat",
                  "not defterini aç"):
        print(f"> {ornek!r} -> {komuttan_ekle(ornek)}")
    print("Liste:", liste())
    print("Özet:", ozet_metin())
