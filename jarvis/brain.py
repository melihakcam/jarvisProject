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
import re
import shutil
import subprocess
import sys
import unicodedata

try:
    from jarvis import config
except ImportError:
    import config

# Sesli okumaya uygunlugu garantilemek icin ek sistem talimati
_SES_TALIMATI = (
    "Sen JARVIS adli sesli asistansin. Cevabin sesli okunacak. "
    "Kisa, akici ve resmi konus; kullaniciya 'efendim' diye hitap et. "
    "Markdown, madde isareti, tablo, emoji veya kod blogu KULLANMA. "
    "Guncel bilgi gerekiyorsa web'de arama yap; ama cevabinda kaynak linki, "
    "URL veya 'Kaynak:' satiri EKLEME, bilgiyi dogal cumleyle soyle. "
    "Kullanici hangi dilde yazdiysa o dilde cevap ver. "
    # --- Bilgisayarda islem yapma yetkisi ---
    "Bu bilgisayarda GERCEKTEN islem yapabilirsin ve yonetici (admin) yetkisiyle "
    "calisiyorsun. Kullanicinin istegini yerine getirmek icin gereken araclari "
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

# Beyne acilan araclar. Web arama + bilgisayarda fiili islem icin Bash ve dosya
# araclari; Skill, docx/pdf/pptx/xlsx gibi belge olusturma yetenekleri icin.
_ARACLAR = ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebSearch", "WebFetch", "Skill"]


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


def _mcp_gerekli(soru: str) -> bool:
    """Soru MCP sunucularina (Gmail, Takvim vb.) ihtiyac duyuyor mu?

    MCP yuklemek her cagriye birkac saniye ekledigi icin sadece e-posta/takvim
    gibi konular gectiginde acilir; 'saat kac' gibi sorularda hizli yol kullanilir.
    """
    if not getattr(config, "MCP_ACIK", False):
        return False
    # Turkce karakterleri sadelestir ki "e-posta"/"eposta" gibi yazimlar da tutsun
    s = (soru or "").lower().replace("ı", "i").replace("-", " ")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return any(k in s for k in config.MCP_ANAHTAR_KELIMELER)


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

    # MCP sunuculari yalnizca gerektiginde yuklenir; gerekmiyorsa
    # --strict-mcp-config ile kapatilir ve her cagride birkac saniye kazanilir.
    mcp_kullan = _mcp_gerekli(soru)
    # MCP araclari da izinli listede olmali, yoksa yuklense bile kullanilamaz.
    araclar = list(_ARACLAR)
    if mcp_kullan:
        araclar += list(config.MCP_ARACLARI)

    komut = [
        _claude_yolu(),
        "-p", istem,
        "--model", config.BEYIN_MODEL,      # hiz icin hizli model (varsayilan: haiku)
        "--append-system-prompt", _SES_TALIMATI,
        "--allowedTools", *araclar,
        # Basli (headless) modda araclari onay beklemeden calistirabilsin diye.
        # Guvenlik, sistem talimatindaki "yikici islemlerde once onay iste" kuraliyla saglanir.
        "--dangerously-skip-permissions",
    ]
    if not mcp_kullan:
        komut.append("--strict-mcp-config")
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
