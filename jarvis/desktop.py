"""JARVIS - Masaustu uygulamasi (Edge uygulama-penceresi + yonetici modu).

Mevcut sinematik paneli GERCEK bir Edge (ya da Chrome) uygulama-penceresinde acar
(sekmesiz, adres cubuksuz, kendi simgesi). Boylece tarayicinin cevrimici ses
tanima motoru (Web Speech API) calisir: dogru, bedava, RAM'siz Turkce STT.
Uygulama acilirken kendini YONETICI (admin) olarak yeniden baslatir.

Sira:
    1) Yonetici degilse -> kendini yonetici olarak yeniden baslat (UAC) ve cik.
    2) 5000 portunu bosalt (takili eski surec varsa kapat).
    3) Flask panel sunucusunu arka planda baslat.
    4) Sunucu hazir olana kadar bekle (/health).
    5) Edge/Chrome'u uygulama-modunda ac; pencere kapanana kadar bekle.
    (Tarayici bulunamazsa pywebview'e duser.)

Calistirma (penceresiz onerilir):
    pythonw jarvis/desktop.py
veya:
    scripts/jarvis_masaustu.vbs
"""
import ctypes
import os
import subprocess
import sys
import threading
import time
import urllib.request

try:
    from jarvis import config
    from jarvis.server import app
except ImportError:
    import config
    from server import app

_HOST = "127.0.0.1"
_PORT = 5000
_URL = f"http://{_HOST}:{_PORT}"
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

_EDGE_YOLLARI = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
_CHROME_YOLLARI = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


# --------------------------------------------------------------------------
# Yonetici (admin) yukseltmesi
# --------------------------------------------------------------------------
def _yonetici_mi() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _yonetici_olarak_yeniden_baslat() -> None:
    """Uygulamayi yonetici olarak yeniden baslatir (UAC penceresi cikar)."""
    betik = os.path.abspath(__file__)
    sonuc = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, f'"{betik}"', None, 1
    )
    if int(sonuc) <= 32:
        print("Yonetici izni verilmedi; uygulama kapatiliyor.")
    sys.exit(0)


# --------------------------------------------------------------------------
# Port / sunucu
# --------------------------------------------------------------------------
def _port_bosalt(port: int) -> None:
    """Verilen portu dinleyen surec varsa kapatir (takili eski JARVIS ornegi)."""
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True,
                             text=True, creationflags=_NO_WINDOW).stdout
        for satir in out.splitlines():
            if f":{port} " in satir and "LISTENING" in satir.upper():
                pid = satir.split()[-1]
                if pid.isdigit() and pid != "0":
                    subprocess.run(["taskkill", "/PID", pid, "/F"],
                                   capture_output=True, creationflags=_NO_WINDOW)
    except Exception as e:
        print("port bosaltma atlandi:", e)


def _sunucuyu_baslat() -> None:
    """Flask panel sunucusunu arka planda (daemon thread) baslatir."""
    def _calis():
        try:
            app.run(host=_HOST, port=_PORT, threaded=True,
                    use_reloader=False, debug=False)
        except Exception as e:
            print("Sunucu baslatilamadi:", e)
    threading.Thread(target=_calis, daemon=True).start()


def _sunucu_hazir_mi(timeout: float = 15.0) -> bool:
    son = time.time() + timeout
    while time.time() < son:
        try:
            with urllib.request.urlopen(f"{_URL}/health", timeout=1) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


# --------------------------------------------------------------------------
# Tarayici (uygulama-modu)
# --------------------------------------------------------------------------
def _tarayici_bul() -> str:
    for yol in _EDGE_YOLLARI + _CHROME_YOLLARI:
        if os.path.exists(yol):
            return yol
    return ""


_PROFIL_AD = "tarayici_profil"   # user-data-dir icin benzersiz iz (surec takibi)


def _profil_pidleri() -> list:
    """Bizim profilimizle acilmis tarayici (Edge/Chrome) sureclerinin PID listesi."""
    pidler = []
    for isim in ("msedge.exe", "chrome.exe"):
        try:
            out = subprocess.run(
                ["wmic", "process", "where", f"name='{isim}'",
                 "get", "commandline,processid"],
                capture_output=True, text=True, creationflags=_NO_WINDOW
            ).stdout or ""
        except Exception:
            out = ""
        for satir in out.splitlines():
            if _PROFIL_AD in satir:
                parcalar = satir.split()
                if parcalar and parcalar[-1].isdigit():
                    pidler.append(parcalar[-1])
    return pidler


def _profil_pencerelerini_kapat() -> None:
    """Onceki denemelerden kalmis (bizim profilimizle acik) tarayici pencerelerini kapatir.
    Boylece izleyici yalnizca yeni acacagimiz tek pencereyi takip eder."""
    for pid in _profil_pidleri():
        try:
            subprocess.run(["taskkill", "/PID", pid, "/F", "/T"],
                           capture_output=True, creationflags=_NO_WINDOW)
        except Exception:
            pass


def _uygulama_penceresi_ac(tarayici: str) -> None:
    """Edge/Chrome'u uygulama-modunda acar ve UYGULAMA PENCERESI kapanana kadar bekler.

    Ayri bir profil klasoru (--user-data-dir) kullaniriz; boylece:
      - mevcut tarayicinizdan bagimsiz, ayri bir surec olur,
      - mikrofon izni bir kez verilince bu profilde kalici olur.

    Not: Chromium baslatici surec pencereyi devredip hemen cikar; bu yuzden
    Popen.wait() ise yaramaz. Bunun yerine profilimize ait tarayici sureci
    kalmayana kadar bekleriz (pencere gercekten kapanana kadar sunucu ayakta kalir).
    """
    profil = str(config.VERI_KLASORU / _PROFIL_AD)
    os.makedirs(profil, exist_ok=True)

    # Onceki denemelerden kalan profil pencerelerini temizle (izleyici sasmasin).
    _profil_pencerelerini_kapat()
    time.sleep(1)

    args = [
        tarayici,
        f"--app={_URL}",
        f"--user-data-dir={profil}",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1280,860",
    ]
    subprocess.Popen(args)   # ates-ve-unut; yasam dongusunu asagida izleriz

    # Yasam dongusu: profil penceresi GORULUP sonra kaybolunca cik.
    # - Titreme onleyici: cikmadan once ust uste 3 kez "yok" gormesi gerekir
    #   (wmic bazen bir an bos donebilir; tek olcumle karar vermeyiz).
    # - Hic gorulmezse guvenli tarafta kalip bekleriz (sunucu ayakta kalir).
    goruldu = False
    yok_sayaci = 0
    while True:
        time.sleep(2)
        if _profil_pidleri():
            goruldu = True
            yok_sayaci = 0
        elif goruldu:
            yok_sayaci += 1
            if yok_sayaci >= 3:
                break                   # pencere gercekten kapandi -> cik


def _pywebview_ac() -> None:
    """Tarayici bulunamazsa yedek: pywebview native penceresi (Web Speech olmayabilir)."""
    try:
        import webview
    except ImportError:
        print("Ne tarayici ne pywebview bulundu; panel acilamiyor.")
        return
    webview.create_window("J.A.R.V.I.S  —  Yönetici", _URL,
                          width=1280, height=800, min_size=(900, 600))
    webview.start()


# --------------------------------------------------------------------------
# Giris noktasi
# --------------------------------------------------------------------------
def main() -> None:
    # 1) Yonetici degilsek kendimizi yukseltip cikalim.
    if not _yonetici_mi():
        _yonetici_olarak_yeniden_baslat()
        return

    # 2) Portu bosalt (takili eski ornek varsa).
    _port_bosalt(_PORT)

    # 3) Panel sunucusunu baslat.
    _sunucuyu_baslat()

    # 4) Sunucunun ayaga kalkmasini bekle.
    if not _sunucu_hazir_mi():
        print("Panel sunucusu zamaninda hazir olmadi.")
        return

    # 5) Uygulama penceresini ac (once gercek tarayici, yoksa pywebview).
    tarayici = _tarayici_bul()
    if tarayici:
        _uygulama_penceresi_ac(tarayici)
    else:
        _pywebview_ac()


if __name__ == "__main__":
    main()
