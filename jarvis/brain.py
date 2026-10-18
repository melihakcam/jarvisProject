"""JARVIS - Beyin (Claude Code).

Kullanicinin sorusunu Claude Code'a (headless / -p modu) gonderir ve cevabi
metin olarak dondurur. Mevcut Claude aboneligini kullanir; ekstra API anahtari
gerektirmez.

Kisilik ve uslup kurallari proje kokundeki CLAUDE.md dosyasindan gelir
(Claude Code proje dizininde calisirken otomatik okur). Ek olarak, sesli
okumaya uygun cevap icin kisa bir sistem talimati da eklenir.

Tek basina test:
    python jarvis/brain.py "merhaba"
    python jarvis/brain.py "Python'da liste nasil ters cevrilir?"
"""
import json
import re
import shutil
import subprocess
import sys
import threading
import time
import unicodedata

try:
    from jarvis import config
except ImportError:
    import config

# Sesli okumaya uygunlugu garantilemek icin ek sistem talimati (her yolda)
_SES_TALIMATI = (
    "Sen JARVIS adli, Melih Akcam'in sesli kisisel asistanisin. Cevabin sesli okunacak. "
    "Kim oldugun sorulursa 'Ben JARVIS, Melih Akçam'ın sesli kişisel asistanıyım efendim.' de. "
    "Kisa (en fazla uc cumle), akici ve resmi konus; kullaniciya 'efendim' diye hitap et. "
    "Markdown, madde isareti, tablo, emoji veya kod blogu KULLANMA. "
    "Kullanici hangi dilde yazdiysa o dilde cevap ver. "
)

# Sadece aracsiz sohbet yolunda eklenir. Islem istekleri (ac/kapat...) zaten
# arac yoluna gider; burada kisitlamalardan bahsetmemesi istenir.
_SOHBET_TALIMATI = (
    "Ne yapabildigin sorulursa sadece yapabildiklerini olumlu sekilde soyle: "
    "uygulama ve siteleri acip kapatabilir, internette arama yapabilir, muzik ve "
    "sesi kontrol edebilir, saati, hava durumunu, doviz kurlarini ve gunun "
    "haberlerini soyleyebilir, ajandaya hatirlatici ekleyebilir, dosya bulup "
    "duzenleyebilir, YouTube videolarini ozetleyebilir, sorulari yanitlayabilir, "
    "Python gibi konularda yardim edebilirsin. Kisitlamalarindan veya "
    "yapamadiklarindan bahsetme. "
)

# Web ve islem yollarinda eklenir
_WEB_TALIMATI = (
    "Guncel bilgi gerekiyorsa web'de arama yap; ama cevabinda kaynak linki, "
    "URL veya 'Kaynak:' satiri EKLEME, bilgiyi dogal cumleyle soyle. "
)

# Sadece islem yolunda eklenir
_ISLEM_TALIMATI = (
    # --- Bilgisayarda islem yapma yetkisi ---
    "Bu bilgisayarda GERCEKTEN islem yapabilirsin; NORMAL kullanici yetkisiyle "
    "calisiyorsun (yonetici degil). Yonetici gerektiren bir islem istenirse "
    "denemek yerine bunu tek cumleyle soyle. Kullanicinin istegini yerine "
    "getirmek icin gereken araclari "
    "(Bash komutlari, dosya okuma/yazma/duzenleme) kullan ve isi FIILEN yap; "
    "sadece nasil yapilacagini anlatma. Windows'tasin; komutlar Windows'a uygun olsun. "
    "Islemi tamamladiktan sonra tek kisa cumleyle teyit et (ornek: 'Klasor olusturuldu efendim.'). "
    "GUVENLIK: Geri donusu olmayan veya riskli islemlerde ONCE ne yapacagini tek "
    "cumleyle soyleyip onay iste; kullanici 'evet' / 'onayliyorum' demeden bunlari YAPMA. "
    "Bunlar: dosya veya klasor silme, bicimlendirme, disk/bolum islemleri, kayit "
    "defteri (registry) veya sistem ayari degisikligi, cok sayida dosyayi ustune yazma, "
    "e-posta/mesaj gonderme, odeme veya para transferi, kurulum/kaldirma. "
    "Emin olmadigin yikici bir istekte de once teyit iste. "
    # --- Belge olusturma (docx/pdf/pptx/xlsx skilleri) ---
    "Word, PDF, PowerPoint veya Excel dosyasi olusturman/duzenlemen istenirse "
    "ilgili Skill aracini kullan. Aksi belirtilmedikce olusturdugun dosyayi "
    "kullanicinin Masaustu klasorune kaydet ve dosya adini tek cumleyle soyle."
)

# Islem yolunda beyne acilan araclar. Web arama + bilgisayarda fiili islem icin
# Bash ve dosya araclari; Skill, docx/pdf/pptx/xlsx gibi belge olusturma icin.
_ARACLAR = ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebSearch", "WebFetch", "Skill"]
# Web yolunda sadece bunlar acilir
_WEB_ARACLARI = ["WebSearch", "WebFetch"]


def _sese_hazirla(metin: str) -> str:
    """Cevabi sesli okumaya uygun hale getirir: markdown link/URL/isaretleri temizler."""
    if not metin:
        return metin
    # [yazi](url) -> yazi
    metin = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", metin)
    # ciplak URL'leri kaldir
    metin = re.sub(r"https?://\S+", "", metin)
    # "Kaynak:" / "Kaynaklar:" ile baslayan satirlari kaldir
    metin = re.sub(r"(?im)^\s*(kaynak(lar)?|source[s]?)\s*:.*$", "", metin)
    # markdown vurgu/isaretleri
    metin = re.sub(r"[*_`#>]+", "", metin)
    # fazla bosluklari topla
    metin = re.sub(r"\n{2,}", "\n", metin)
    metin = re.sub(r"[ \t]{2,}", " ", metin)
    return metin.strip()


def _surum_anahtari(klasor):
    """'2.1.219' gibi klasor adini siralanabilir sayi demetine cevirir."""
    try:
        return tuple(int(p) for p in klasor.name.split("."))
    except ValueError:
        return ()


_yol_onbellegi = None


def _claude_yolu() -> str:
    """Claude Code'un tam yolunu bulur.

    Once PATH'e bakar. Bulamazsa config.CLAUDE_ARAMA_KLASORLERI altinda
    claude.exe arar - Claude masaustu uygulamasi CLI'yi surum numarali bir
    klasore kurar ve PATH'e EKLEMEZ, bu yuzden en yeni surum secilir.
    Sonuc onbelleklenir; her soruda disk taranmaz.
    """
    global _yol_onbellegi
    if _yol_onbellegi is not None:
        return _yol_onbellegi

    yol = shutil.which(config.CLAUDE_KOMUTU)
    if yol is None:
        for kok in config.CLAUDE_ARAMA_KLASORLERI:
            if not kok.is_dir():
                continue
            # Dogrudan klasorun icinde mi?
            for ad in ("claude.exe", "claude.cmd", "claude"):
                if (kok / ad).is_file():
                    yol = str(kok / ad)
                    break
            if yol:
                break
            # Surum numarali alt klasorlerde mi? (en yeniden eskiye)
            for alt in sorted(kok.iterdir(), key=_surum_anahtari, reverse=True):
                if not alt.is_dir():
                    continue
                for ad in ("claude.exe", "claude.cmd", "claude"):
                    if (alt / ad).is_file():
                        yol = str(alt / ad)
                        break
                if yol:
                    break
            if yol:
                break

    _yol_onbellegi = yol or config.CLAUDE_KOMUTU
    return _yol_onbellegi


def _sadelestir(metin: str) -> str:
    """Kucuk harf, Turkce karaktersiz, noktalamasiz hale getirir.

    Boylece "e-posta"/"eposta", "Klasörü"/"klasoru" gibi yazimlar ayni tutar.
    """
    s = (metin or "").lower().replace("ı", "i").replace("-", " ")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _kelime_gecer(s: str, kelimeler) -> bool:
    """Sadelestirilmis metinde kelimelerden biri kelime basindan geciyor mu?"""
    s = f" {s} "
    return any(f" {k}" in s for k in kelimeler)


def _mcp_gerekli(soru: str) -> bool:
    """Soru MCP sunucularina (Gmail, Takvim vb.) ihtiyac duyuyor mu?

    MCP yuklemek her cagriye birkac saniye ekledigi icin sadece e-posta/takvim
    gibi konular gectiginde acilir; 'saat kac' gibi sorularda hizli yol kullanilir.
    """
    if not getattr(config, "MCP_ACIK", False):
        return False
    s = _sadelestir(soru)
    return any(k in s for k in config.MCP_ANAHTAR_KELIMELER)


def _yol_sec(soru: str) -> str:
    """Sorunun gidecegi yol: "islem", "web" ya da "sohbet" (config'e bakin)."""
    s = _sadelestir(soru)
    if _kelime_gecer(s, config.ISLEM_ANAHTAR_KELIMELER):
        return "islem"
    if _kelime_gecer(s, config.WEB_ANAHTAR_KELIMELER):
        return "web"
    return "sohbet"


def _tarihli(istem: str) -> str:
    """Sohbet yolunda Claude Code'un varsayilan talimati (ve icindeki tarih)
    gitmedigi icin su anki tarih/saat soruya eklenir."""
    return f"(Su an: {time.strftime('%d.%m.%Y %H:%M')})\n{istem}"


def _sohbet_bayraklari():
    """Sohbet yolu: aracsiz, skill'siz, kullanici ayarsiz; Claude Code'un uzun
    varsayilan sistem talimati yerine sadece JARVIS talimati (~5400 yerine
    ~2000 token). Sabit kalmali ki onceden acilan surecte de ayni olsun."""
    return [
        "--model", config.BEYIN_MODEL,
        "--setting-sources", "project,local",
        "--no-session-persistence",
        "--disable-slash-commands",
        "--strict-mcp-config",
        "--system-prompt", _SES_TALIMATI + _SOHBET_TALIMATI,
        "--tools", "",
    ]


# ---------------------------------------------------------------------------
# Hazir bekleyen surec: Claude Code'un her soruda ~2 sn suren acilisi, bir
# sonraki sohbet sorusu icin onceden yapilir. Surec soruyu stdin'den bekler,
# TEK soruyu cevaplayip kapanir (oturum birikmez, token artmaz); hemen yerine
# yenisi acilir. Hazir surec yoksa/olduyse normal (soguk) cagriya dusulur.
# ---------------------------------------------------------------------------
_hazir_kilit = threading.Lock()
_hazir = {"surec": None, "zaman": 0.0}
_HAZIR_OMUR = 30 * 60   # saniye; daha eski hazir surec kapatilip yenilenir


def _hazir_surec_ac():
    return subprocess.Popen(
        [_claude_yolu(), "-p", "--input-format", "stream-json",
         "--output-format", "stream-json", "--verbose", *_sohbet_bayraklari()],
        cwd=str(config.PROJE_KOKU),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def onceden_hazirla():
    """Bir sonraki sohbet sorusu icin Claude surecini arka planda acar."""
    if not getattr(config, "BEYIN_HAZIR_BEKLET", False):
        return
    with _hazir_kilit:
        p = _hazir["surec"]
        if p is not None and p.poll() is None and time.time() - _hazir["zaman"] < _HAZIR_OMUR:
            return
        if p is not None:
            _kapat(p)
        try:
            _hazir["surec"], _hazir["zaman"] = _hazir_surec_ac(), time.time()
        except OSError as e:
            print("[Beyin] hazir surec acilamadi:", e)
            _hazir["surec"] = None


def _kapat(p):
    try:
        p.kill()
    except OSError:
        pass


def _hazirdan_sor(istem: str):
    """Hazir surece sorar. Cevap metni, ya da kullanilamadiysa None."""
    if not getattr(config, "BEYIN_HAZIR_BEKLET", False):
        return None
    with _hazir_kilit:
        p, zaman = _hazir["surec"], _hazir["zaman"]
        _hazir["surec"] = None
    # Kullanilan surecin yerine hemen yenisi acilsin (bu soru cevaplanirken)
    threading.Thread(target=onceden_hazirla, daemon=True).start()
    if p is None or p.poll() is not None or time.time() - zaman >= _HAZIR_OMUR:
        if p is not None:
            _kapat(p)
        return None

    mesaj = json.dumps({"type": "user", "message": {"role": "user", "content": istem}})
    try:
        cikti, _ = p.communicate(mesaj + "\n", timeout=config.BEYIN_ZAMAN_ASIMI)
    except (OSError, ValueError, subprocess.TimeoutExpired) as e:
        print("[Beyin] hazir surec hatasi:", e)
        _kapat(p)
        return None
    for satir in reversed((cikti or "").splitlines()):
        try:
            d = json.loads(satir)
        except ValueError:
            continue
        if d.get("type") == "result":
            cevap = (d.get("result") or "").strip()
            if d.get("is_error") or not cevap:
                return None
            return cevap
    return None


def dusun(soru: str, gecmis_metni: str = None) -> str:
    """Soruyu Claude'a gonderir, sesli okunmaya uygun metin cevabi dondurur.

    gecmis_metni verilirse (son konusmalar), soru bu baglamla birlikte gonderilir
    ve JARVIS onceki konusmayi hatirlar. Bos/None ise davranis eskisiyle aynidir.
    """
    soru = (soru or "").strip()
    if not soru:
        return ""

    gecmis_metni = (gecmis_metni or "").strip()
    if gecmis_metni:
        istem = (
            "Önceki konuşmamız:\n"
            f"{gecmis_metni}\n\n"
            f"Şimdiki soru: {soru}"
        )
    else:
        istem = soru

    yol = _yol_sec(soru)
    # MCP sunuculari yalnizca gerektiginde yuklenir; gerekmiyorsa
    # --strict-mcp-config ile kapatilir ve her cagride birkac saniye kazanilir.
    mcp_kullan = _mcp_gerekli(soru)
    if mcp_kullan:
        yol = "islem"

    komut = [
        _claude_yolu(),
        "-p", istem,
        "--model", config.BEYIN_MODEL,      # hiz icin hizli model (varsayilan: haiku)
        # Kullanici klasorundeki eklenti/ayarlar yuklenmez (CLAUDE.md proje
        # dosyasi oldugu icin yine okunur), oturum diske yazilmaz.
        "--setting-sources", "project,local",
        "--no-session-persistence",
    ]
    if yol == "islem":
        # MCP araclari da izinli listede olmali, yoksa yuklense bile kullanilamaz.
        araclar = list(_ARACLAR)
        if mcp_kullan:
            araclar += list(config.MCP_ARACLARI)
        komut += [
            "--append-system-prompt", _SES_TALIMATI + _WEB_TALIMATI + _ISLEM_TALIMATI,
            "--allowedTools", *araclar,
            # Basli (headless) modda araclari onay beklemeden calistirabilsin diye.
            # Guvenlik, sistem talimatindaki "yikici islemlerde once onay iste" kuraliyla saglanir.
            "--dangerously-skip-permissions",
        ]
    else:
        # Skill listesi ve gereksiz arac tanimlari gonderilmez: hiz + token tasarrufu
        komut += ["--disable-slash-commands"]
        if yol == "web":
            komut += [
                "--append-system-prompt", _SES_TALIMATI + _WEB_TALIMATI,
                "--tools", ",".join(_WEB_ARACLARI),
                "--allowedTools", *_WEB_ARACLARI,
            ]
        else:
            # Sohbet: once onceden acilip bekleyen surec denenir (~2 sn kazanc)
            baslangic = time.monotonic()
            cevap = _hazirdan_sor(_tarihli(istem))
            if cevap is not None:
                print(f"[Beyin] yol=sohbet(hazir) sure={time.monotonic() - baslangic:.1f}sn")
                return _sese_hazirla(cevap)
            komut = [komut[0], "-p", _tarihli(istem), *_sohbet_bayraklari()]
    if not mcp_kullan and yol != "sohbet":
        komut.append("--strict-mcp-config")

    baslangic = time.monotonic()
    try:
        sonuc = subprocess.run(
            komut,
            cwd=str(config.PROJE_KOKU),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=config.BEYIN_ZAMAN_ASIMI,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError:
        return ("Claude Code bulunamadi efendim. Kurulu oldugundan ve PATH'te "
                "yer aldigindan emin olun.")
    except subprocess.TimeoutExpired:
        return "Uzgunum efendim, cevap zaman asimina ugradi."
    finally:
        print(f"[Beyin] yol={yol} sure={time.monotonic() - baslangic:.1f}sn")

    if sonuc.returncode != 0:
        hata = (sonuc.stderr or "").lower()
        if any(x in hata for x in ("network", "connect", "internet", "econnrefused",
                                   "getaddrinfo", "fetch failed", "timeout", "enotfound")):
            return ("Su an internet baglantisi yok gibi gorunuyor efendim. "
                    "Bilgisayar komutlarinizi yerine getirebilirim ama sorulariniza "
                    "cevap vermem icin baglanti gerekiyor.")
        return ("Beyne ulasirken bir sorun olustu efendim. Claude Code'un acik ve "
                "girisli oldugundan emin olun.")

    return _sese_hazirla((sonuc.stdout or "").strip())


if __name__ == "__main__":
    if len(sys.argv) > 1:
        soru = " ".join(sys.argv[1:])
    else:
        soru = "Kendini kisaca tanit."
    print(f"[Soru]: {soru}")
    print("[Dusunuyor...]")
    cevap = dusun(soru)
    print(f"[JARVIS]: {cevap}")
