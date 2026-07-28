"""JARVIS - Izole ses tanima testi.

Mikrofondan 5 saniye kayit alir, Whisper ile cozer ve TAM olarak ne
anlasildigini yazdirir. Boylece ses tanimayi panelden bagimsiz test ederiz.
"""
import os
import sys
import time

BURA = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(BURA)
sys.path.insert(0, os.path.join(KOK, "jarvis"))

import numpy as np
import sounddevice as sd
import config
import stt
from faster_whisper import WhisperModel

SURE = 5  # saniye

dev = sd.query_devices(kind="input")
hiz = int(dev.get("default_samplerate") or 44100)
print("Mikrofon :", dev["name"])
print("Kayit hizi:", hiz, "Hz")
print("Model    :", config.WHISPER_MODEL, "- yukleniyor...")
model = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type=config.WHISPER_COMPUTE)

print("\n" + "=" * 46)
print(f"  {SURE} SANIYE BOYUNCA KONUS  (geri sayim sonrasi)")
print("  Ornek:  Merhaba Jarvis, not defterini ac")
print("=" * 46)
for i in (3, 2, 1):
    print(f"  ... {i}")
    time.sleep(1)
print("  >>> KONUS! <<<\n")

ses = sd.rec(int(SURE * hiz), samplerate=hiz, channels=1, dtype="float32")
sd.wait()
ses = ses.flatten().astype(np.float32)

rms = float(np.sqrt(np.mean(ses ** 2)))
tepe = float(np.max(np.abs(ses)))
print(f"Ses seviyesi: RMS={rms:.4f}  tepe={tepe:.3f}")
if tepe < 0.01:
    print("!! Ses cok kisik/gelmemis olabilir - mikrofon izni/seviyesini kontrol et.")

if tepe > 1e-4:
    ses = (ses * min(0.95 / tepe, 12.0)).astype(np.float32)

ses16 = stt.ses_16k(ses, hiz)
metin = stt.whisper_coz(model, ses16, np)

print("\n" + "#" * 46)
print("  DUYULAN:", repr(metin))
print("#" * 46)
