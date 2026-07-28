"""JARVIS - Ana dongu.

Hepsini birlestirir:
    push-to-talk -> STT (ses->yazi) -> yerel komut? -> degilse BEYIN (Claude) -> TTS (sesli cevap)

Calistirma:
    python jarvis/main.py

Kullanim:
    - Konusmak icin BOSLUK tusuna basili tut, konus, birak.
    - Cikmak icin Ctrl+C ya da "kapan" / "kapat kendini" de.
"""
import sys

# Hem "python jarvis/main.py" hem "python -m jarvis.main" ile calissin
try:
    from jarvis import config, stt, tts, brain
    from jarvis import commands
except ImportError:
    import config, stt, tts, brain
    import commands

# Sesli cikis komutlari
CIKIS_KELIMELERI = ("kapan", "kapat kendini", "kendini kapat", "gorusuruz jarvis",
                    "kapan jarvis", "cikis yap")


def _cikis_mi(metin: str) -> bool:
    m = metin.lower().strip()
    return any(k in m for k in CIKIS_KELIMELERI)


def calistir():
    print("=" * 50)
    print("  J.A.R.V.I.S  -  baslatiliyor...")
    print("=" * 50)

    dinleyici = stt.Dinleyici()
    konusmaci = tts.Konusmaci()

    konusmaci.konus(config.UYANMA_MESAJI)
    print(f"\n[JARVIS]: {config.UYANMA_MESAJI}")
    print(f"\n[Konusmak icin '{config.PUSH_TO_TALK_TUSU}' basili tut. Cikmak icin Ctrl+C.]\n")

    try:
        while True:
            metin = dinleyici.dinle()
            if not metin:
                continue

            print(f"[Sen]: {metin}")

            if _cikis_mi(metin):
                konusmaci.konus("Kapaniyorum efendim. Iyi gunler.")
                break

            # 1) Once yerel komut mu? (uygulama ac, arama yap vb. - Claude'a gitmeden)
            cevap = commands.calistir(metin)

            # 2) Yerel komut degilse beyne (Claude) sor
            if cevap is None:
                print("[Dusunuyor...]")
                cevap = brain.dusun(metin)

            print(f"[JARVIS]: {cevap}\n")
            konusmaci.konus(cevap)

    except KeyboardInterrupt:
        print("\n[Ctrl+C ile cikildi.]")
        try:
            konusmaci.konus("Kapaniyorum efendim.")
        except Exception:
            pass


if __name__ == "__main__":
    calistir()
