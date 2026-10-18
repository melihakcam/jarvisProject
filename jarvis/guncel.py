"""JARVIS - Guncel veriler: doviz kuru (TCMB) ve haber basliklari (RSS).

Bu bilgiler icin beyne (Claude + web arama) gitmek ~15 sn ve token harcar;
burada resmi/bilinen kaynaklardan dogrudan okunur (1 sn alti, sifir token).
Kaynaga ulasilamazsa fonksiyonlar None dondurur, soru beyne yonlenir.

Tek basina test:
    python jarvis/guncel.py
"""
import re
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET

# TCMB gosterge kurlari (her is gunu 15:30'da aciklanir, ucretsiz, anahtarsiz)
_TCMB_URL = "https://www.tcmb.gov.tr/kurlar/today.xml"
# Haber kaynaklari: sirayla denenir, ilk cevap veren kullanilir
_HABER_KAYNAKLARI = (
    ("Anadolu Ajansı", "https://www.aa.com.tr/tr/rss/default?cat=guncel"),
    ("TRT Haber", "https://www.trthaber.com/manset_articles.rss"),
)
_ONBELLEK_SURESI = 10 * 60   # saniye; ayni veriyi her soruda yeniden indirme

_kilit = threading.Lock()
_onbellek = {}   # anahtar -> (zaman, veri)


def _getir(url: str, zaman_asimi: int = 5) -> bytes:
    istek = urllib.request.Request(url, headers={"User-Agent": "JARVIS/1.0"})
    with urllib.request.urlopen(istek, timeout=zaman_asimi) as yanit:
        return yanit.read()


def _onbellekli(anahtar, uret):
    with _kilit:
        kayit = _onbellek.get(anahtar)
        if kayit and time.time() - kayit[0] < _ONBELLEK_SURESI:
            return kayit[1]
    try:
        veri = uret()
    except Exception as e:
        print(f"[guncel] {anahtar} alinamadi:", e)
        return None
    if veri:
        with _kilit:
            _onbellek[anahtar] = (time.time(), veri)
    return veri


def kurlar():
    """TCMB doviz satis kurlari: {"tarih": "16.10.2026", "USD": 49.44, ...} ya da None."""
    def uret():
        kok = ET.fromstring(_getir(_TCMB_URL))
        sonuc = {"tarih": kok.get("Tarih", "")}
        for doviz in kok.findall("Currency"):
            kod = doviz.get("CurrencyCode")
            satis = (doviz.findtext("ForexSelling") or "").strip()
            if kod and satis:
                sonuc[kod] = float(satis)
        return sonuc if "USD" in sonuc else None
    return _onbellekli("kur", uret)


def basliklar(adet: int = 3):
    """En guncel haber basliklari: ("Kaynak adi", [baslik, ...]) ya da None."""
    def uret():
        for ad, url in _HABER_KAYNAKLARI:
            try:
                kok = ET.fromstring(_getir(url))
            except Exception as e:
                print(f"[guncel] {ad} alinamadi:", e)
                continue
            liste = []
            for oge in kok.iter("item"):
                baslik = re.sub(r"\s+", " ", oge.findtext("title") or "").strip()
                if baslik and baslik not in liste:
                    liste.append(baslik)
            if liste:
                return (ad, liste)
        return None
    sonuc = _onbellekli("haber", uret)
    if not sonuc:
        return None
    return (sonuc[0], sonuc[1][:adet])


if __name__ == "__main__":
    print(kurlar())
    print(basliklar())
