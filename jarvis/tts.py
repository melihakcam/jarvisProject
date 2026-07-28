"""JARVIS - Yazi -> Ses (TTS).

pyttsx3 kullanir: Windows'un dahili SAPI seslerini kullanir.
Tamamen ucretsiz ve offline calisir, internet gerektirmez.

Tek basina test:
    python jarvis/tts.py
    python jarvis/tts.py "Merhaba efendim, ben Jarvis."
"""
import sys

try:
    import pyttsx3
except ImportError:
    print("pyttsx3 kurulu degil. Kurmak icin: pip install pyttsx3")
    sys.exit(1)

# config'i hem "python jarvis/tts.py" hem de "python -m jarvis.tts" ile calisacak sekilde al
try:
    from jarvis import config
except ImportError:
    import config  # dogrudan jarvis/ klasoru icinden calistirilirsa


class Konusmaci:
    """JARVIS'in sesi. Metni alir, hoparlorden okur."""

    def __init__(self):
        self._motor = pyttsx3.init()
        self._motor.setProperty("rate", config.TTS_HIZI)
        self._motor.setProperty("volume", config.TTS_SES_SEVIYESI)
        self._sesi_sec(config.TTS_SES_TERCIHI)

    def _sesi_sec(self, tercih: str) -> None:
        """Tercih edilen ismi iceren ilk sesi secer; bulamazsa varsayilani birakir."""
        if not tercih:
            return
        for ses in self._motor.getProperty("voices"):
            if tercih.lower() in ses.name.lower():
                self._motor.setProperty("voice", ses.id)
                return

    def sesleri_listele(self) -> None:
        """Sistemde yuklu tum sesleri yazdirir (config icin isim secmek uzere)."""
        print("Sistemdeki sesler:")
        for i, ses in enumerate(self._motor.getProperty("voices")):
            diller = ", ".join(ses.languages) if ses.languages else "?"
            print(f"  [{i}] {ses.name}  (dil: {diller})")

    def konus(self, metin: str) -> None:
        """Verilen metni sesli okur (bloklar; bitene kadar bekler)."""
        if not metin or not metin.strip():
            return
        self._motor.say(metin)
        self._motor.runAndWait()


# main.py'nin paylasilan tek bir konusmaci kullanmasi icin yardimci
_ortak_konusmaci = None


def konus(metin: str) -> None:
    """Kolay kullanim: jarvis.tts.konus('...')."""
    global _ortak_konusmaci
    if _ortak_konusmaci is None:
        _ortak_konusmaci = Konusmaci()
    _ortak_konusmaci.konus(metin)


if __name__ == "__main__":
    konusmaci = Konusmaci()
    if len(sys.argv) > 1 and sys.argv[1] == "--sesler":
        konusmaci.sesleri_listele()
    else:
        metin = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else \
            "Sistemler cevrimici efendim. Ben Jarvis, emrinizi bekliyorum."
        print(f"Okunuyor: {metin}")
        konusmaci.konus(metin)
        print("Bitti.")
