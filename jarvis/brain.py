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
    "Kullanici hangi dilde yazdiysa o dilde cevap ver."
)

# Beyne acilan araclar: guncel bilgi icin web arama (salt-okunur, guvenli)
_ARACLAR = ["WebSearch", "WebFetch"]


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


def dusun(soru: str) -> str:
    """Soruyu Claude'a gonderir, sesli okunmaya uygun metin cevabi dondurur."""
    soru = (soru or "").strip()
    if not soru:
        return ""

    komut = [
        _claude_yolu(),
        "-p", soru,
        "--append-system-prompt", _SES_TALIMATI,
        "--allowedTools", *_ARACLAR,
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
