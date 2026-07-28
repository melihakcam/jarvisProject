"""JARVIS - Panelin hizli komut butonlarinin gercek eylemleri.

ODAK MODU  -> Windows bildirim balonlarini gercekten kapatir/acar
BRIFING    -> saat, hava, ajanda ve sistem durumundan gercek ozet uretir
YEDEKLE    -> projeyi ve verileri D:\\jarvis-backups altina zip'ler
KILITLE    -> Windows oturumunu gercekten kilitler

Tek basina test:
    python jarvis/eylemler.py brifing
"""
import datetime
import os
import pathlib
import subprocess
import threading
import zipfile

try:
    from jarvis import config, telemetry, weather, ajanda
except ImportError:
    import config, telemetry, weather, ajanda

_GIZLI = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Yedekler proje ile ayni surucunun kokunde tutulur (C:'ye hicbir sey yazilmaz).
YEDEK_KLASORU = pathlib.Path(telemetry.PROJE_SURUCUSU) / "jarvis-backups"

# Yedege dahil edilmeyecek klasorler (buyuk ve yeniden uretilebilir)
_HARIC = {"models", "__pycache__", ".git", "node_modules", ".venv", "venv"}


# --------------------------------------------------------------------------
# ODAK MODU - Windows bildirimleri
# --------------------------------------------------------------------------
_TOAST_YOLU = r"SOFTWARE\Microsoft\Windows\CurrentVersion\PushNotifications"
_QUIET_YOLU = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Notifications\Settings"


def _toast_oku() -> bool:
    """Bildirim balonlari acik mi (gercek kayit defteri degeri)."""
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _TOAST_YOLU) as k:
            return winreg.QueryValueEx(k, "ToastEnabled")[0] != 0
    except FileNotFoundError:
        return True
    except OSError:
        return True


def _toast_yaz(acik: bool):
    import winreg
    deger = 1 if acik else 0
    for yol, ad in ((_TOAST_YOLU, "ToastEnabled"),
                    (_QUIET_YOLU, "NOC_GLOBAL_SETTING_TOASTS_ENABLED")):
        try:
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, yol, 0,
                                    winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, ad, 0, winreg.REG_DWORD, deger)
        except OSError:
            pass


def odak_modu(ac=None):
    """Odak modunu acar/kapatir. ac=None ise mevcut durumu tersine cevirir."""
    su_an_acik = not _toast_oku()          # bildirimler kapaliysa odak modu acik
    hedef = (not su_an_acik) if ac is None else bool(ac)
    _toast_yaz(not hedef)
    if hedef:
        return {"ok": True, "state": True,
                "answer": "Odak modu etkin efendim. Windows bildirimleri susturuldu.",
                "log": "odak modu açıldı — bildirimler kapatıldı."}
    return {"ok": True, "state": False,
            "answer": "Odak modu kapatıldı efendim. Bildirimler yeniden açık.",
            "log": "odak modu kapatıldı — bildirimler açıldı."}


def odak_durumu() -> bool:
    return not _toast_oku()


# --------------------------------------------------------------------------
# YEDEKLE
# --------------------------------------------------------------------------
_yedek_durum = {"calisiyor": False, "son": None}


def _yedek_calistir():
    YEDEK_KLASORU.mkdir(parents=True, exist_ok=True)
    damga = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    hedef = YEDEK_KLASORU / f"jarvis_{damga}.zip"
    kok = config.PROJE_KOKU
    sayi = 0
    with zipfile.ZipFile(hedef, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for klasor, altlar, dosyalar in os.walk(kok):
            altlar[:] = [a for a in altlar if a not in _HARIC]
            for d in dosyalar:
                tam = os.path.join(klasor, d)
                if tam == str(hedef) or d.endswith((".zip", ".log", ".tmp")):
                    continue
                try:
                    z.write(tam, os.path.relpath(tam, kok))
                    sayi += 1
                except OSError:
                    continue
    boyut = hedef.stat().st_size / 1024 ** 2
    _yedek_durum["calisiyor"] = False
    _yedek_durum["son"] = {"dosya": str(hedef), "adet": sayi, "mb": round(boyut, 1),
                           "zaman": datetime.datetime.now().isoformat(timespec="seconds")}
    return _yedek_durum["son"]


def yedekle():
    """Projeyi ve verileri gercekten zip'ler (arka planda calisir)."""
    if _yedek_durum["calisiyor"]:
        return {"ok": False, "answer": "Yedekleme zaten sürüyor efendim.",
                "log": "yedekleme zaten çalışıyor."}
    _yedek_durum["calisiyor"] = True

    sonuc = {}

    def _is():
        try:
            sonuc.update(_yedek_calistir())
        except Exception as e:
            _yedek_durum["calisiyor"] = False
            sonuc["hata"] = str(e)

    is_parcacigi = threading.Thread(target=_is)
    is_parcacigi.start()
    is_parcacigi.join(timeout=25)          # kucuk projede saniyeler surer

    if is_parcacigi.is_alive():
        return {"ok": True, "answer": "Yedekleme başladı efendim, arka planda sürüyor.",
                "log": f"yedekleme başladı — hedef {YEDEK_KLASORU}"}
    if "hata" in sonuc:
        return {"ok": False, "answer": f"Yedekleme başarısız oldu efendim: {sonuc['hata']}",
                "log": f"yedekleme hatası: {sonuc['hata']}"}
    return {"ok": True,
            "answer": (f"Yedekleme tamamlandı efendim. {sonuc['adet']} dosya, "
                       f"{sonuc['mb']} megabayt olarak {YEDEK_KLASORU.name} "
                       f"klasörüne kaydedildi."),
            "log": f"yedekleme tamamlandı — {sonuc['adet']} dosya, {sonuc['mb']} MB.",
            "detay": sonuc}


def son_yedek():
    """En son yedegin gercek zamani ve boyutu."""
    if _yedek_durum["son"]:
        return _yedek_durum["son"]
    try:
        zipler = sorted(YEDEK_KLASORU.glob("jarvis_*.zip"),
                        key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return None
    if not zipler:
        return None
    en_son = zipler[0]
    return {"dosya": str(en_son), "mb": round(en_son.stat().st_size / 1024 ** 2, 1),
            "zaman": datetime.datetime.fromtimestamp(
                en_son.stat().st_mtime).isoformat(timespec="seconds")}


# --------------------------------------------------------------------------
# KILITLE
# --------------------------------------------------------------------------
def kilitle():
    """Windows oturumunu gercekten kilitler."""
    try:
        subprocess.Popen("rundll32.exe user32.dll,LockWorkStation",
                         shell=True, creationflags=_GIZLI)
        return {"ok": True, "answer": "Bilgisayarı kilitliyorum efendim.",
                "log": "oturum kilitlendi."}
    except Exception as e:
        return {"ok": False, "answer": f"Kilitleyemedim efendim: {e}",
                "log": f"kilitleme hatası: {e}"}


# --------------------------------------------------------------------------
# BRIFING
# --------------------------------------------------------------------------
_GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
_AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
          "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def brifing():
    """Saat, hava, ajanda, sistem ve uyarilardan gercek gunluk brifing uretir."""
    simdi = datetime.datetime.now()
    if simdi.hour < 6:
        selam = "İyi geceler efendim"
    elif simdi.hour < 12:
        selam = "Günaydın efendim"
    elif simdi.hour < 18:
        selam = "İyi günler efendim"
    else:
        selam = "İyi akşamlar efendim"

    parcalar = [
        f"{selam}. Saat {simdi.strftime('%H:%M')}, "
        f"bugün {simdi.day} {_AYLAR[simdi.month - 1]} {_GUNLER[simdi.weekday()]}.",
        weather.ozet_metin(),
        ajanda.ozet_metin(),
        telemetry.ozet_metin(),
    ]

    kritik = [u["text"] for u in telemetry.uyarilar()
              if u.get("level") == "kritik"]
    if kritik:
        parcalar.append("Dikkatinizi çekerim: " + " ".join(kritik))

    return " ".join(p for p in parcalar if p)


EYLEMLER = {
    "odak": odak_modu,
    "yedekle": yedekle,
    "kilitle": kilitle,
}


if __name__ == "__main__":
    import sys
    ad = sys.argv[1] if len(sys.argv) > 1 else "brifing"
    if ad == "brifing":
        print(brifing())
    elif ad in EYLEMLER:
        print(EYLEMLER[ad]())
    else:
        print("Kullanim: python jarvis/eylemler.py [brifing|odak|yedekle|kilitle]")
