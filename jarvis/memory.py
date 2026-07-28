"""JARVIS - Hafiza (konusma gecmisi).

Her soru-cevap adimini bir JSON dosyasina kaydeder ve son konusmalari beyne
verilecek duz metin baglam olarak dondurur. Boylece JARVIS "az once ne dedik"i
hatirlar (baglamsal hafiza).

Kayit yapisi (duz giris listesi, adim adim rol etiketli):
    [
      {"zaman": "2026-07-28T14:35:02", "rol": "kullanici", "metin": "saat kac"},
      {"zaman": "2026-07-28T14:35:03", "rol": "jarvis", "metin": "Saat ... efendim."}
    ]

Tek basina test:
    python jarvis/memory.py
"""
import json
import os
from datetime import datetime

try:
    from jarvis import config
except ImportError:
    import config

# Dosyada tutulacak azami giris sayisi (sisme olmasin). Tam arsiv istenirse
# bu degeri buyutun ya da None yapin.
_AZAMI_GIRIS = 1000

_ROL_ETIKET = {"kullanici": "Kullanıcı", "jarvis": "JARVIS"}


def yukle() -> list:
    """Konusma gecmisini okur. Dosya yoksa/bozuksa bos liste dondurur."""
    yol = config.KONUSMA_GECMISI_YOLU
    try:
        with open(yol, "r", encoding="utf-8") as f:
            veri = json.load(f)
        if isinstance(veri, list):
            return veri
    except (FileNotFoundError, ValueError, OSError):
        pass
    return []


def _yaz(gecmis: list) -> None:
    """Gecmisi diske atomik yazar (gecici dosya + replace)."""
    yol = config.KONUSMA_GECMISI_YOLU
    try:
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        gecici = f"{yol}.tmp"
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(gecmis, f, ensure_ascii=False, indent=2)
        os.replace(gecici, yol)
    except OSError as e:
        # Hafiza yazilamazsa uygulama cokmesin; sadece uyar.
        print("Hafiza yazilamadi:", e)


def ekle(rol: str, metin: str) -> None:
    """Tek bir giris ekler (zaman damgasiyla) ve diske yazar."""
    metin = (metin or "").strip()
    if not metin:
        return
    gecmis = yukle()
    gecmis.append({
        "zaman": datetime.now().isoformat(timespec="seconds"),
        "rol": rol,
        "metin": metin,
    })
    if _AZAMI_GIRIS and len(gecmis) > _AZAMI_GIRIS:
        gecmis = gecmis[-_AZAMI_GIRIS:]
    _yaz(gecmis)


def tur_kaydet(soru: str, cevap: str) -> None:
    """Bir konusma turunu kaydeder: once kullanici sorusu, sonra JARVIS cevabi."""
    ekle("kullanici", soru)
    ekle("jarvis", cevap)


def son_baglam(n: int) -> str:
    """Son n girisi beyne verilecek duz metin blogu olarak dondurur.

    Ornek cikti:
        Kullanıcı: saat kac
        JARVIS: Saat on dort otuz bes efendim.
    """
    if not n or n <= 0:
        return ""
    gecmis = yukle()
    if not gecmis:
        return ""
    satirlar = []
    for giris in gecmis[-n:]:
        etiket = _ROL_ETIKET.get(giris.get("rol", ""), giris.get("rol", ""))
        metin = (giris.get("metin") or "").strip()
        if metin:
            satirlar.append(f"{etiket}: {metin}")
    return "\n".join(satirlar)


if __name__ == "__main__":
    print("[test] tur kaydediliyor...")
    tur_kaydet("deneme soru", "deneme cevap efendim")
    print(f"[test] dosya: {config.KONUSMA_GECMISI_YOLU}")
    print("[test] son baglam:")
    print(son_baglam(config.HAFIZA_BAGLAM_ADEDI))
