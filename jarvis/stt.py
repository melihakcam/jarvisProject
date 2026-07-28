"""JARVIS - Ses -> Yazi (STT).

Vosk kullanir: offline, ucretsiz, Turkce. Push-to-talk mantigi ile calisir:
belirlenen tusa (varsayilan BOSLUK) basili tutarsin, konusursun, birakinca
konusma yaziya cevrilir.

Tek basina test:
    python jarvis/stt.py
"""
import json
import queue
import sys

try:
    import sounddevice as sd
    import vosk
except ImportError as e:
    print(f"Gerekli paket eksik ({e.name}). Kurmak icin: pip install vosk sounddevice keyboard")
    sys.exit(1)

try:
    import keyboard
except ImportError:
    print("keyboard kurulu degil. Kurmak icin: pip install keyboard")
    sys.exit(1)

try:
    from jarvis import config
except ImportError:
    import config

vosk.SetLogLevel(-1)  # Vosk'un ayrintili loglarini sustur


class Dinleyici:
    """Mikrofonu dinler, konusmayi yaziya cevirir (push-to-talk)."""

    def __init__(self):
        if not config.VOSK_MODEL_YOLU.exists():
            print(f"Vosk modeli bulunamadi: {config.VOSK_MODEL_YOLU}")
            print("README.md'deki adimlarla Turkce modeli models/ klasorune indirin.")
            sys.exit(1)
        self._model = vosk.Model(str(config.VOSK_MODEL_YOLU))
        self._hiz = config.ORNEKLEME_HIZI
        self._kuyruk: queue.Queue = queue.Queue()

    def _ses_geldi(self, indata, frames, time, status):
        self._kuyruk.put(bytes(indata))

    def dinle(self) -> str:
        """PTT tusuna basilana kadar bekler; basili tutuldugu surece dinler;
        birakinca cozulen metni dondurur."""
        tus = config.PUSH_TO_TALK_TUSU
        taniyici = vosk.KaldiRecognizer(self._model, self._hiz)

        print(f"[Konusmak icin '{tus}' tusuna basili tutun...]")
        keyboard.wait(tus)  # tusa basilmasini bekle

        # Kuyrukta birikmis eski sesi temizle
        while not self._kuyruk.empty():
            self._kuyruk.get_nowait()

        print("[Dinliyorum...]")
        with sd.RawInputStream(samplerate=self._hiz, blocksize=8000,
                               dtype="int16", channels=1,
                               callback=self._ses_geldi):
            while keyboard.is_pressed(tus):
                try:
                    veri = self._kuyruk.get(timeout=0.2)
                except queue.Empty:
                    continue
                taniyici.AcceptWaveform(veri)

        sonuc = json.loads(taniyici.FinalResult())
        metin = sonuc.get("text", "").strip()
        print(f"[Anlasilan]: {metin!r}")
        return metin


class AkisKaydedici:
    """Panel/sunucu icin: baslat() ile kayda basla, bitir() ile metni al.
    Push-to-talk tusuna gerek yok; sunucu HTTP istekleriyle kontrol eder."""

    def __init__(self):
        if not config.VOSK_MODEL_YOLU.exists():
            raise FileNotFoundError(f"Vosk modeli bulunamadi: {config.VOSK_MODEL_YOLU}")
        self._model = vosk.Model(str(config.VOSK_MODEL_YOLU))
        self._hiz = config.ORNEKLEME_HIZI
        self._stream = None
        self._rec = None

    def _ses_geldi(self, indata, frames, time, status):
        if self._rec is not None:
            self._rec.AcceptWaveform(bytes(indata))

    def baslat(self) -> None:
        """Mikrofonu acar ve kayda baslar."""
        self._rec = vosk.KaldiRecognizer(self._model, self._hiz)
        self._stream = sd.RawInputStream(samplerate=self._hiz, blocksize=8000,
                                         dtype="int16", channels=1,
                                         callback=self._ses_geldi)
        self._stream.start()

    def bitir(self) -> str:
        """Kaydi durdurur ve cozulen metni dondurur."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        metin = ""
        if self._rec is not None:
            metin = json.loads(self._rec.FinalResult()).get("text", "").strip()
            self._rec = None
        return metin


def ses_16k(ses, kaynak_hiz):
    """Sesi 16 kHz'e (Whisper'in bekledigi hiza) kaliteli sekilde donusturur."""
    import numpy as np
    ses = np.asarray(ses, dtype=np.float32).flatten()
    if kaynak_hiz == 16000 or ses.size == 0:
        return ses
    try:
        from scipy.signal import resample_poly
        from math import gcd
        g = gcd(int(kaynak_hiz), 16000)
        return resample_poly(ses, 16000 // g, kaynak_hiz // g).astype(np.float32)
    except Exception:
        # scipy yoksa dogrusal interpolasyon (yedek)
        n = int(round(len(ses) * 16000 / kaynak_hiz))
        x_old = np.linspace(0, 1, num=len(ses), endpoint=False)
        x_new = np.linspace(0, 1, num=n, endpoint=False)
        return np.interp(x_new, x_old, ses).astype(np.float32)


# Whisper'i Turkce'ye ve asistan konusma bicimine yonlendiren baglam ipucu.
# Dogru dil secimini ve gunluk asistan kelimelerini tanimayi belirgin iyilestirir.
_TR_IPUCU = ("Merhaba efendim. Bu bir Türkçe sesli asistan konuşmasıdır. "
             "Kullanıcı JARVIS'e komut veriyor: uygulama aç, saat kaç, hava nasıl, "
             "not defterini aç, müziği durdur gibi.")

_WHISPER_AYAR = dict(
    language="tr",
    beam_size=5,
    vad_filter=True,                                   # sessizligi ayikla (halusinasyonu kirar)
    vad_parameters=dict(min_silence_duration_ms=400),
    condition_on_previous_text=False,
    temperature=0.0,
    no_speech_threshold=0.6,
    initial_prompt=_TR_IPUCU,                          # Turkce/asistan baglami -> daha dogru
)


def sesi_yukselt(ses, np=None):
    """Kisik mikrofonu tepe seviyeye normalize eder (halusinasyon yerine gercek algi).
    Whisper'in dogru anlamasi icin dusuk sesi belirgin iyilestirir."""
    if np is None:
        import numpy as np
    ses = np.asarray(ses, dtype=np.float32).flatten()
    if ses.size == 0:
        return ses
    tepe = float(np.max(np.abs(ses)))
    if tepe > 1e-4:
        ses = (ses * min(0.95 / tepe, 12.0)).astype(np.float32)
    return ses


def whisper_coz(model, ses16, np=None):
    """16 kHz float ses dizisini Whisper ile Turkce metne cevirir."""
    segmentler, _ = model.transcribe(ses16, **_WHISPER_AYAR)
    return " ".join(s.text for s in segmentler).strip()


def whisper_model_yukle():
    """Panel sunucusunun paylasacagi Whisper modelini yukler."""
    from faster_whisper import WhisperModel
    return WhisperModel(config.WHISPER_MODEL, device="cpu",
                        compute_type=config.WHISPER_COMPUTE)


def dosyadan_coz(model, dosya_yolu: str) -> str:
    """Ses dosyasini (webm/wav/ogg...) Whisper ile Turkce metne cevirir.

    Tarayicidan gelen ses genelde kisik ve sikistirilmis olur; onu 16 kHz'e cozup
    tepe seviyeye yukseltiyoruz. Bu, model boyutunu buyutmeden dogrulugu artirir.
    Cozme/yukseltme bir nedenle basarisiz olursa dogrudan dosya yolundan cozeriz.
    """
    try:
        import numpy as np
        from faster_whisper.audio import decode_audio
        ses16 = decode_audio(dosya_yolu, sampling_rate=16000)
        if ses16 is None or np.asarray(ses16).size < 4000:   # ~0.25 sn'den kisa
            return ""
        ses16 = sesi_yukselt(ses16, np)
        return whisper_coz(model, ses16, np)
    except Exception as e:
        print("[STT] on-isleme atlandi, dogrudan cozuluyor:", e)
        segmentler, _ = model.transcribe(dosya_yolu, **_WHISPER_AYAR)
        return " ".join(s.text for s in segmentler).strip()


class WhisperKaydedici:
    """Panel/sunucu icin, Whisper tabanli (cok daha dogru Turkce tanima).
    Mikrofonu KENDI dogal hizinda kaydeder, sonra 16 kHz'e cevirir.
    baslat() ile tamponlar, bitir() ile cozer."""

    def __init__(self):
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise ImportError("faster-whisper kurulu degil. Kurun: pip install faster-whisper")
        import numpy as np
        self._np = np
        self._model = WhisperModel(config.WHISPER_MODEL, device="cpu",
                                   compute_type=config.WHISPER_COMPUTE)
        # mikrofonun dogal ornekleme hizini kullan (zorla 16k isteme -> bozulmayi onler)
        try:
            dev = sd.query_devices(kind="input")
            self._kayit_hizi = int(dev.get("default_samplerate") or 44100)
        except Exception:
            self._kayit_hizi = 44100
        self._parcalar = []
        self._stream = None

    def _ses_geldi(self, indata, frames, time, status):
        self._parcalar.append(indata.copy())

    def baslat(self) -> None:
        self._parcalar = []
        self._stream = sd.InputStream(samplerate=self._kayit_hizi, channels=1,
                                      dtype="float32", callback=self._ses_geldi)
        self._stream.start()

    def bitir(self) -> str:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._parcalar:
            return ""
        np = self._np
        ses = np.concatenate(self._parcalar, axis=0).flatten().astype(np.float32)
        sure = ses.shape[0] / self._kayit_hizi
        if sure < 0.25:                       # yanlislikla cok kisa dokunma
            return ""
        rms = float(np.sqrt(np.mean(ses ** 2)))
        # ses seviyesini yukselt (kisik mikrofon -> halusinasyon yerine gercek algi)
        ses = sesi_yukselt(ses, np)
        ses16 = ses_16k(ses, self._kayit_hizi)
        metin = whisper_coz(self._model, ses16, np)
        print(f"[STT] hiz={self._kayit_hizi} sure={sure:.1f}s rms={rms:.4f} -> {metin!r}")
        return metin


def kaydedici_olustur():
    """config.STT_MOTORU'na gore uygun kaydediciyi olusturur.
    Whisper secili ama yuklenemezse Vosk'a duser."""
    if config.STT_MOTORU == "whisper":
        try:
            return WhisperKaydedici()
        except Exception as e:
            print(f"[STT] Whisper baslatilamadi ({e}); Vosk'a geciliyor.")
    return AkisKaydedici()


# Ortak tek dinleyici (main.py icin)
_ortak_dinleyici = None


def dinle() -> str:
    """Kolay kullanim: jarvis.stt.dinle()."""
    global _ortak_dinleyici
    if _ortak_dinleyici is None:
        _ortak_dinleyici = Dinleyici()
    return _ortak_dinleyici.dinle()


if __name__ == "__main__":
    dinleyici = Dinleyici()
    print("STT testi. Cikmak icin Ctrl+C.")
    try:
        while True:
            metin = dinleyici.dinle()
            if metin:
                print(f"  -> Sen dedin ki: {metin}")
            else:
                print("  -> (bir sey anlasilmadi)")
    except KeyboardInterrupt:
        print("\nCikildi.")
