"""JARVIS - Yerel bilgisayar kontrol komutlari.

Bu modul, LLM (Claude) gerektirmeyen dogrudan bilgisayar islemlerini yapar:
uygulama acma/kapama, internette arama, site acma, ses/medya kontrolu,
pencere yonetimi, saat/tarih. Boylece bu komutlar aninda, ucretsiz ve
internet gerektirmeden calisir.

Kullanim:
    cevap = commands.calistir("not defterini ac")
    # -> "Tabii efendim, Not Defteri aciliyor."  (komut anlasildi)
    cevap = commands.calistir("hayatin anlami nedir")
    # -> None  (yerel komut degil; main.py bunu beyne yonlendirir)

Yani: bir metni ISLEDIYSE cevap metnini, ISLEMEDIYSE None dondurur.
"""
import datetime
import glob
import os
import subprocess
import unicodedata
import webbrowser

try:
    import keyboard  # ses/medya tuslari icin (zaten bagimlilik)
except ImportError:
    keyboard = None


# --------------------------------------------------------------------------
# Uygulama tanimlari:  anahtar kelimeler -> (calistirma hedefi, kapatma imaji)
# --------------------------------------------------------------------------
UYGULAMALAR = {
    ("not defteri", "notepad", "not defterini"): ("notepad", "notepad.exe"),
    ("hesap makinesi", "hesap makinesini", "calculator"): ("calc", "CalculatorApp.exe"),
    ("paint", "resim"): ("mspaint", "mspaint.exe"),
    ("chrome", "google chrome"): ("chrome", "chrome.exe"),
    ("tarayici", "internet", "browser"): ("", ""),   # varsayilan tarayici (ozel)
    ("dosya gezgini", "dosyalar", "gezgin", "explorer"): ("explorer", "explorer.exe"),
    ("komut istemi", "cmd", "terminal"): ("cmd", "cmd.exe"),
    ("ayarlar", "settings"): ("ms-settings:", ""),
    ("word", "microsoft word"): ("winword", "WINWORD.EXE"),
    ("excel", "microsoft excel"): ("excel", "EXCEL.EXE"),
    ("spotify",): ("spotify", "Spotify.exe"),
    ("gorev yoneticisi", "task manager"): ("taskmgr", "Taskmgr.exe"),
}

# Site kisayollari: anahtar kelime -> URL
SITELER = {
    ("youtube",): "https://www.youtube.com",
    ("google",): "https://www.google.com",
    ("gmail", "mail", "e posta", "eposta"): "https://mail.google.com",
    ("github",): "https://github.com",
    ("whatsapp",): "https://web.whatsapp.com",
    ("twitter", "x "): "https://twitter.com",
    ("instagram",): "https://www.instagram.com",
    ("chatgpt",): "https://chat.openai.com",
    ("hava durumu", "hava"): "https://www.google.com/search?q=hava+durumu",
}


def _sadelestir(metin: str) -> str:
    """Turkce karakterleri ASCII'ye indirger (aç->ac, kaç->kac, ışık->isik).
    Vosk'un urettigi Turkce metni, ASCII anahtar kelimelerle eslestirmek icin."""
    s = (metin or "").lower().replace("ı", "i")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s


def _normalize(metin: str) -> str:
    return " " + _sadelestir(metin.strip() if metin else "") + " "


# pythonw altinda alt sureclerin konsol penceresi acmamasi icin
_GIZLI = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _baslat(hedef: str) -> None:
    """Bir uygulamayi/hedefi baslatir (PATH ve App Paths uzerinden)."""
    subprocess.Popen(f'start "" "{hedef}"', shell=True, creationflags=_GIZLI)


def _kapat(imaj: str) -> bool:
    """Verilen exe imajini kapatir. Basarili ise True."""
    sonuc = subprocess.run(["taskkill", "/IM", imaj, "/F"],
                           capture_output=True, text=True, creationflags=_GIZLI)
    return sonuc.returncode == 0


# --------------------------------------------------------------------------
# Komut isleyicileri  (islerse cevap str, islemezse None)
# --------------------------------------------------------------------------
def _saat_tarih(t: str):
    if "saat kac" in t or " saat " in t and "kac" in t:
        s = datetime.datetime.now().strftime("%H:%M")
        return f"Saat su an {s} efendim."
    if "bugun gunlerden" in t or "hangi gun" in t or ("tarih" in t and "ne" in t) or "bugunun tarihi" in t:
        bugun = datetime.datetime.now()
        gunler = ["Pazartesi", "Sali", "Carsamba", "Persembe", "Cuma", "Cumartesi", "Pazar"]
        aylar = ["Ocak", "Subat", "Mart", "Nisan", "Mayis", "Haziran", "Temmuz",
                 "Agustos", "Eylul", "Ekim", "Kasim", "Aralik"]
        return (f"Bugun {bugun.day} {aylar[bugun.month-1]} {bugun.year}, "
                f"{gunler[bugun.weekday()]} efendim.")
    return None


def _uygulama_ac(t: str):
    if "ac" not in t and "baslat" not in t:
        return None
    # Once site mi?
    for kelimeler, url in SITELER.items():
        if any(k in t for k in kelimeler):
            webbrowser.open(url)
            return f"Tabii efendim, {kelimeler[0]} aciliyor."
    # Uygulama mi?
    for kelimeler, (hedef, _imaj) in UYGULAMALAR.items():
        if any(k in t for k in kelimeler):
            if hedef == "":  # varsayilan tarayici
                webbrowser.open("https://www.google.com")
            else:
                _baslat(hedef)
            return f"Tabii efendim, {kelimeler[0]} aciliyor."
    return None


def _uygulama_kapat(t: str):
    if "kapat" not in t:
        return None
    for kelimeler, (_hedef, imaj) in UYGULAMALAR.items():
        if imaj and any(k in t for k in kelimeler):
            if _kapat(imaj):
                return f"Tabii efendim, {kelimeler[0]} kapatildi."
            return f"{kelimeler[0]} zaten kapali gorunuyor efendim."
    return None


def _internette_ara(t: str):
    # "internette X ara" / "X arat" / "google'da X ara"
    tetik = None
    for kalip in ("internette ", "google da ", "google'da ", "aramada ", "web de "):
        if kalip in t:
            tetik = kalip
            break
    if tetik is None and t.strip().endswith("ara "):
        tetik = ""  # "hava durumu ara" gibi

    if tetik is None and " ara " not in t and not t.strip().endswith("ara "):
        return None

    # Arama sorgusunu ayikla
    sorgu = t
    for temizle in ("internette", "google da", "google'da", "aramada", "web de",
                    "arat", "ara", "jarvis"):
        sorgu = sorgu.replace(temizle, " ")
    sorgu = " ".join(sorgu.split()).strip()
    if not sorgu:
        return None
    webbrowser.open(f"https://www.google.com/search?q={sorgu.replace(' ', '+')}")
    return f"Tabii efendim, {sorgu} icin internette arama yapiyorum."


def _dosya_bul(t: str):
    if "dosya" not in t or ("bul" not in t and "ara" not in t):
        return None
    # Cok basit: kullanicinin belgelerinde/masaustunde isim gecen dosyalari arar.
    # "X dosyasini bul" -> X'i ayikla
    sorgu = t
    for temizle in ("dosyasini", "dosyasi", "dosyayi", "dosya", "isimli", "adli",
                    "bul", "ara", "jarvis"):
        sorgu = sorgu.replace(temizle, " ")
    sorgu = " ".join(sorgu.split()).strip()
    if not sorgu:
        return "Hangi dosyayi arayayim efendim?"

    kok = os.path.expanduser("~")
    bulunanlar = []
    for klasor in ("Desktop", "Documents", "Downloads", "Masaüstü", "Belgeler", "İndirilenler"):
        yol = os.path.join(kok, klasor)
        if os.path.isdir(yol):
            bulunanlar += glob.glob(os.path.join(yol, f"*{sorgu}*"))
    if not bulunanlar:
        return f"{sorgu} ile eslesen bir dosya bulamadim efendim."
    # Ilk bulunani Gezgin'de goster
    ilk = bulunanlar[0]
    subprocess.Popen(f'explorer /select,"{ilk}"', shell=True, creationflags=_GIZLI)
    ad = os.path.basename(ilk)
    if len(bulunanlar) == 1:
        return f"{ad} adli dosyayi buldum ve gosteriyorum efendim."
    return f"{len(bulunanlar)} dosya buldum efendim; ilki {ad}, onu gosteriyorum."


def _ses_medya(t: str):
    if keyboard is None:
        return None
    if "sesi ac" in t or "sesi yukselt" in t or "ses ac" in t:
        for _ in range(5):
            keyboard.send("volume up")
        return "Sesi yukselttim efendim."
    if "sesi kis" in t or "sesi azalt" in t or "sesi indir" in t:
        for _ in range(5):
            keyboard.send("volume down")
        return "Sesi kistim efendim."
    if "sesi kapat" in t or "sessize al" in t or "sustur" in t:
        keyboard.send("volume mute")
        return "Sesi kapattim efendim."
    if "duraklat" in t or "durdur" in t or "devam et" in t or "oynat" in t:
        keyboard.send("play/pause media")
        return "Tamamdir efendim."
    if "sonraki sarki" in t or "sonraki parca" in t or "gec" in t:
        keyboard.send("next track")
        return "Sonraki parcaya geciyorum efendim."
    if "onceki sarki" in t or "onceki parca" in t:
        keyboard.send("previous track")
        return "Onceki parcaya donuyorum efendim."
    return None


def _pencere(t: str):
    if keyboard is None:
        return None
    if "pencereleri kucult" in t or "masaustunu goster" in t or "hepsini kucult" in t:
        keyboard.send("windows+d")
        return "Masaustunu gosteriyorum efendim."
    if "pencereyi kucult" in t:
        keyboard.send("windows+down")
        return "Pencereyi kucultuyorum efendim."
    if "pencereyi buyut" in t or "tam ekran" in t:
        keyboard.send("windows+up")
        return "Pencereyi buyutuyorum efendim."
    return None


def _sistem(t: str):
    if "bilgisayari kilitle" in t or "ekrani kilitle" in t:
        subprocess.Popen("rundll32.exe user32.dll,LockWorkStation", shell=True, creationflags=_GIZLI)
        return "Bilgisayari kilitliyorum efendim."
    return None


# Sirayla denenecek isleyiciler
_ISLEYICILER = (_saat_tarih, _uygulama_ac, _uygulama_kapat, _internette_ara,
                _dosya_bul, _ses_medya, _pencere, _sistem)


def calistir(metin: str):
    """Metni yerel komut olarak islemeye calisir.
    Islerse cevap metnini, islemezse None dondurur."""
    t = _normalize(metin)
    for isleyici in _ISLEYICILER:
        try:
            cevap = isleyici(t)
        except Exception as e:
            return f"Komutu uygularken bir sorun oldu efendim: {e}"
        if cevap is not None:
            return cevap
    return None


if __name__ == "__main__":
    import sys
    ornekler = [
        "not defterini ac", "saat kac", "bugun gunlerden ne",
        "hesap makinesini ac", "youtube ac", "internette python ara",
    ]
    if len(sys.argv) > 1:
        ornekler = [" ".join(sys.argv[1:])]
    for o in ornekler:
        print(f"> {o!r}  ->  {calistir(o)!r}")
