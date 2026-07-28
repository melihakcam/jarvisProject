"""JARVIS - Yerel bilgisayar kontrol komutlari.

Bu modul cogunlukla LLM (Claude) gerektirmeyen dogrudan bilgisayar islemlerini
yapar: uygulama acma/kapama, internette arama, site acma, ses/medya kontrolu,
pencere yonetimi, saat/tarih, dosya duzenleme. Bu komutlar aninda, ucretsiz ve
internet gerektirmeden calisir.

Tek istisna: YouTube video ozetleme (_youtube_ozet). Video linki tanindiginda
transkript burada (yerel) indirilir, ama ozeti yazmak icin beyne (Claude)
basvurulur - bu yuzden diger komutlardan daha yavas ve internet+abonelik gerektirir.

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
import re
import subprocess
import unicodedata
import webbrowser

try:
    import keyboard  # ses/medya tuslari icin (zaten bagimlilik)
except ImportError:
    keyboard = None

try:
    from youtube_transcript_api import YouTubeTranscriptApi  # video ozetleme icin
except ImportError:
    YouTubeTranscriptApi = None


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


# --------------------------------------------------------------------------
# Ozel klasorler (Masaustu / Belgeler / Indirilenler)
#
# Bu klasorler OneDrive'a tasinmis olabilir (ornegin
# C:\Users\ad\OneDrive\Masaustu). Bu yuzden "~/Desktop" varsaymak yerine
# Windows'un kayit defterindeki gercek yollari okuruz.
# --------------------------------------------------------------------------
_KAYIT_ANAHTARI = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
_KAYIT_ADLARI = {
    "masaustu": ("Desktop", ("Desktop", "Masaüstü")),
    "belgeler": ("Personal", ("Documents", "Belgeler")),
    "indirilenler": ("{374DE290-123F-4565-9164-39C4925E467B}", ("Downloads", "İndirilenler")),
}


def _ozel_klasor(tur: str):
    """'masaustu' / 'belgeler' / 'indirilenler' icin gercek yolu dondurur.
    Bulunamazsa None."""
    kayit_adi, yedek_adlar = _KAYIT_ADLARI[tur]
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KAYIT_ANAHTARI) as anahtar:
            ham, _tur = winreg.QueryValueEx(anahtar, kayit_adi)
        yol = os.path.expandvars(ham)
        if os.path.isdir(yol):
            return yol
    except (ImportError, OSError):
        pass
    # Kayit defteri okunamadiysa klasik yerlere bak
    kok = os.path.expanduser("~")
    for ad in yedek_adlar:
        yol = os.path.join(kok, ad)
        if os.path.isdir(yol):
            return yol
    return None


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

    bulunanlar = []
    for tur in ("masaustu", "belgeler", "indirilenler"):
        yol = _ozel_klasor(tur)
        if yol:
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


def _ag_durumu(t: str):
    """'hangi wifi', 'hangi aga bagliyim', 'internet baglantim nasil' gibi sorular."""
    wifi_sorusu = ("wifi" in t or "wi fi" in t or "kablosuz" in t
                   or ("hangi" in t and ("ag" in t or "internet" in t)))
    baglanti_sorusu = ("internet" in t and any(k in t for k in
                       ("nasil", "var mi", "calisiyor", "durumu", "hizi")))
    if not (wifi_sorusu or baglanti_sorusu):
        return None

    try:
        from jarvis import telemetry
    except ImportError:
        import telemetry

    w = telemetry.wifi_bilgisi()
    if not w.get("ssid"):
        return "Kablosuz bir aga bagli degilsiniz efendim, baglanti kablolu gorunuyor."

    cevap = f"{w['ssid']} adli kablosuz aga baglisiniz efendim"
    if w.get("signal"):
        cevap += f", sinyal gucu {w['signal'].rstrip('%')} yuzde"
    if w.get("band"):
        cevap += f", {w['band']} bandinda"
    return cevap + "."


def _sistem(t: str):
    if "bilgisayari kilitle" in t or "ekrani kilitle" in t:
        subprocess.Popen("rundll32.exe user32.dll,LockWorkStation", shell=True, creationflags=_GIZLI)
        return "Bilgisayari kilitliyorum efendim."
    return None


# --------------------------------------------------------------------------
# Dosya duzenleyici: bir klasordeki gevsek dosyalari turune gore alt
# klasorlere tasir (Resimler, Belgeler, Videolar, Muzik, Sikistirilmis, Diger).
# Sadece dosyalari tasir; var olan alt klasorlere dokunmaz.
# --------------------------------------------------------------------------
_DUZEN_KLASORLERI = {
    ("masaustu", "masaustunu", "masaustundeki"): ("masaustu", "Masaüstü"),
    ("indirilenler", "indirilenleri", "indirilenlerdeki", "downloads"): ("indirilenler", "İndirilenler"),
    ("belgeler", "belgelerimi", "belgelerdeki", "documents"): ("belgeler", "Belgeler"),
}

_TUR_UZANTILARI = {
    "Resimler": (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"),
    "Belgeler": (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv"),
    "Videolar": (".mp4", ".mkv", ".avi", ".mov", ".wmv"),
    "Muzik": (".mp3", ".wav", ".flac", ".m4a"),
    "Sikistirilmis": (".zip", ".rar", ".7z", ".tar", ".gz"),
}


def _hedef_klasor_adi(uzanti: str) -> str:
    for ad, uzantilar in _TUR_UZANTILARI.items():
        if uzanti.lower() in uzantilar:
            return ad
    return "Diger"


def _dosya_duzenle(t: str):
    if "duzenle" not in t:
        return None
    for kelimeler, (klasor_turu, klasor_tr) in _DUZEN_KLASORLERI.items():
        if not any(k in t for k in kelimeler):
            continue
        yol = _ozel_klasor(klasor_turu)
        if yol is None:
            return f"{klasor_tr} klasorunu bulamadim efendim."

        tasinan = 0
        for ad in os.listdir(yol):
            kaynak = os.path.join(yol, ad)
            if not os.path.isfile(kaynak):
                continue  # alt klasorlere dokunma
            uzanti = os.path.splitext(ad)[1]
            if not uzanti or uzanti.lower() == ".lnk":
                continue  # kisayollari ve uzantisiz dosyalari atla
            hedef_ad = _hedef_klasor_adi(uzanti)
            hedef_klasor = os.path.join(yol, hedef_ad)
            os.makedirs(hedef_klasor, exist_ok=True)
            hedef = os.path.join(hedef_klasor, ad)
            if os.path.exists(hedef):
                continue  # ayni isimli dosya zaten tasinmis, uzerine yazma
            try:
                os.rename(kaynak, hedef)
                tasinan += 1
            except OSError:
                continue

        if tasinan == 0:
            return f"{klasor_tr} zaten duzenli gorunuyor efendim, tasinacak dosya bulamadim."
        return f"{klasor_tr} klasorunu duzenledim efendim, {tasinan} dosyayi turune gore ayirdim."
    return None


# --------------------------------------------------------------------------
# YouTube video ozetleme: "<link> ozetle" gibi istekleri isler. Video ID'si
# buyuk/kucuk harfe duyarli oldugu icin BU ISLEYICI HAM (normalize edilmemis)
# metni alir, digerleri gibi normalize edilmis metni degil.
# --------------------------------------------------------------------------
_YOUTUBE_URL_DESENI = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)"
    r"([A-Za-z0-9_-]{11})"
)


def _youtube_video_id(ham_metin: str):
    eslesme = _YOUTUBE_URL_DESENI.search(ham_metin or "")
    return eslesme.group(1) if eslesme else None


def _youtube_ozet(ham_metin: str):
    video_id = _youtube_video_id(ham_metin)
    if video_id is None:
        return None
    if "ozet" not in _sadelestir(ham_metin):
        return None  # link var ama ozetle denmemis; baska bir istek olabilir

    if YouTubeTranscriptApi is None:
        return ("Video ozetleyebilmem icin 'youtube-transcript-api' kutuphanesi "
                "gerekiyor efendim. requirements.txt guncel, 'pip install -r "
                "requirements.txt' ile kurabilirsiniz.")

    api = YouTubeTranscriptApi()
    try:
        transkript = api.fetch(video_id, languages=["tr", "en"])
    except Exception:
        # Turkce/Ingilizce yoksa videoda hangi dil varsa onu al
        try:
            mevcut = list(api.list(video_id))
            transkript = api.fetch(video_id, languages=[mevcut[0].language_code])
        except Exception:
            return "Bu videonun altyazisi/transkripti yok gibi gorunuyor efendim, ozetleyemedim."

    metin_birlesik = " ".join(parca.text for parca in transkript).strip()
    if not metin_birlesik:
        return "Bu videonun transkripti bos gorunuyor efendim."

    try:
        from jarvis import brain
    except ImportError:
        import brain

    istem = (
        "Asagidaki YouTube video transkriptini Turkce, 3-4 cumleyle, sesli "
        "okumaya uygun sekilde ozetle:\n\n" + metin_birlesik[:8000]
    )
    return brain.dusun(istem)


# Sirayla denenecek isleyiciler (normalize edilmis metinle calisanlar)
_ISLEYICILER = (_saat_tarih, _ag_durumu, _uygulama_ac, _uygulama_kapat,
                _internette_ara, _dosya_bul, _dosya_duzenle, _ses_medya, _pencere, _sistem)


def calistir(metin: str):
    """Metni yerel komut olarak islemeye calisir.
    Islerse cevap metnini, islemezse None dondurur."""
    try:
        cevap = _youtube_ozet(metin)  # ham metinle, harf buyuklugu korunmali
    except Exception as e:
        return f"Videoyu ozetlerken bir sorun oldu efendim: {e}"
    if cevap is not None:
        return cevap

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
