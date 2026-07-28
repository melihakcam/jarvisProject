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
    "Emin olmadigin yikici bir istekte de once teyit iste."
)

# Beyne acilan araclar. Web arama + bilgisayarda fiili islem icin Bash ve dosya araclari.
_ARACLAR = ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebSearch", "WebFetch"]


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


def _claude_yolu() -> str:
    """Windows'ta 'claude' bir .cmd olabilir; tam yolu bulur."""
    yol = shutil.which(config.CLAUDE_KOMUTU)
    return yol or config.CLAUDE_KOMUTU


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

    komut = [
        _claude_yolu(),
        "-p", istem,
        "--append-system-prompt", _SES_TALIMATI,
        "--allowedTools", *_ARACLAR,
        # Basli (headless) modda araclari onay beklemeden calistirabilsin diye.
        # Guvenlik, sistem talimatindaki "yikici islemlerde once onay iste" kuraliyla saglanir.
        "--dangerously-skip-permissions",
    ]
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
