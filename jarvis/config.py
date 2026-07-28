"""JARVIS - Merkezi ayarlar.

Tum ayarlari buradan degistirebilirsiniz. Diger moduller bu dosyayi okur.
"""
from pathlib import Path

# --- Yollar ---
PROJE_KOKU = Path(__file__).resolve().parent.parent
MODEL_KLASORU = PROJE_KOKU / "models"
VERI_KLASORU = PROJE_KOKU / "data"

# Vosk ses modeli klasoru (indirilen model buraya cikarilir)
# Kucuk Turkce model: vosk-model-small-tr-0.3  (~50 MB, hafif)
VOSK_MODEL_YOLU = MODEL_KLASORU / "vosk-model-small-tr-0.3"

# --- Ses girisi (STT) ---
ORNEKLEME_HIZI = 16000        # 16kHz
PUSH_TO_TALK_TUSU = "space"   # Basili tutunca dinler
CIKIS_TUSU = "esc"

# STT motoru: "whisper" (cok daha dogru, onerilen) veya "vosk" (hafif ama zayif)
STT_MOTORU = "whisper"
# Whisper model boyutu: "tiny", "base", "small", "medium"
#   small = iyi denge (onerilen) | base = daha hizli | medium = en dogru ama yavas
WHISPER_MODEL = "small"
WHISPER_COMPUTE = "int8"      # CPU icin hizli ve hafif

# --- Ses cikisi (TTS) ---
TTS_HIZI = 175                # kelime/dakika (varsayilan ~200)
TTS_SES_SEVIYESI = 1.0        # 0.0 - 1.0
# Tercih edilen ses ismi parcasi (Windows sesleri). Bos ise varsayilan ses.
# Ornek Turkce ses: "Tolga"  |  Ingilizce: "David", "Zira"
TTS_SES_TERCIHI = "Tolga"

# --- Beyin (Claude Code) ---
CLAUDE_KOMUTU = "claude"      # once PATH'te aranir
# PATH'te bulunamazsa buradaki klasorlerde claude.exe aranir (en yeni surum
# secilir). Claude masaustu uygulamasi CLI'yi buraya kurar ama PATH'e eklemez.
CLAUDE_ARAMA_KLASORLERI = [
    Path.home() / "AppData" / "Roaming" / "Claude" / "claude-code",
    Path.home() / ".claude" / "local",
]
BEYIN_ZAMAN_ASIMI = 180       # saniye (bilgisayarda islem yapan gorevler daha uzun surebilir)
# Beyin modeli: sesli asistan icin HIZ onemli. "haiku" en hizlisi (onerilen).
#   Daha akilli ama yavas isterseniz: "sonnet" ya da "opus".
BEYIN_MODEL = "haiku"

# --- MCP baglantilari (Gmail, Takvim vb.) ---
# MCP sunuculari her cagride yeniden yuklenir ve bu birkac saniye ekler. Sesli
# asistanda bu gecikme rahatsiz edicidir; bu yuzden MCP SADECE ihtiyac duyulan
# sorularda acilir. Asagidaki kelimelerden biri soruda geciyorsa MCP yuklenir,
# gecmiyorsa hizli yol (MCP'siz) kullanilir.
# Google kimlik bilgileri (.gauth.json) kurulana kadar KAPALI. Kurulum
# tamamlaninca True yapmak yeterlidir; kalan her sey hazir.
MCP_ACIK = False
# .mcp.json icinde tanimli sunucularin arac on ekleri. MCP araclari da izinli
# arac listesine eklenmezse beyin onlari goremez, bu yuzden burada sayilirlar.
MCP_ARACLARI = ("mcp__google-calendar",)
MCP_ANAHTAR_KELIMELER = (
    # e-posta
    "mail", "e posta", "eposta", "gmail", "posta kutusu", "gelen kutusu",
    # takvim / ajanda
    "takvim", "toplanti", "randevu", "etkinlik", "davet", "musait",
    # ingilizce
    "email", "calendar", "meeting", "appointment", "schedule",
)

# --- Hafiza (konusma gecmisi) ---
# Tum konusmalar bu JSON dosyasina adim adim (kim ne dedi) kaydedilir.
KONUSMA_GECMISI_YOLU = VERI_KLASORU / "konusmalar.json"
# Beyne baglam olarak verilecek son giris sayisi (~5 tur). Buyutmek daha uzun
# hafiza demektir ama beynin cevap suresini uzatabilir.
HAFIZA_BAGLAM_ADEDI = 10

# --- Genel ---
VARSAYILAN_DIL = "tr"         # "tr" veya "en"
UYANMA_MESAJI = "Sistemler cevrimici efendim. Emrinizi bekliyorum."
