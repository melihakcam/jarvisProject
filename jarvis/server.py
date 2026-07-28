"""JARVIS - Yerel panel sunucusu.

Kontrol panelini (panel/index.html) yerel bir web adresinde yayinlar ve panelin
mikrofon butonunu gercek sesli asistana baglar:

    Panel mic butonu (basili tut)  ->  /listen/start
    birak                          ->  /listen/stop
        -> Vosk (ses->yazi) -> yerel komut? degilse Claude beyni -> TTS (sesli cevap)
        -> panele {heard, answer} doner

Calistirma:
    python jarvis/server.py
Sonra tarayicida:  http://localhost:5000

Not: jarvis_baslat.bat bunu penceresiz (pythonw) baslatir ve paneli acar.
"""
import threading

from flask import Flask, jsonify, request, send_from_directory

try:
    from jarvis import config, stt, tts, brain, commands, memory
except ImportError:
    import config, stt, tts, brain, commands, memory

import os
import sys
import tempfile
# pythonw (penceresiz) altinda stdout/stderr None olabilir; bu, ilk log/print
# denemesinde sunucuyu cokertir. Ciktilari bir log dosyasina yonlendirerek
# hem cokmeyi onleriz hem de hatalari server.log'da gorebiliriz.
try:
    _log = open(config.PROJE_KOKU / "server.log", "a", encoding="utf-8", buffering=1)
    sys.stdout = _log
    sys.stderr = _log
except Exception:
    pass

PANEL_KLASORU = str(config.PROJE_KOKU / "panel")

app = Flask(__name__, static_folder=PANEL_KLASORU, static_url_path="")

# Paylasilan bilesenler (ilk kullanimda yuklenir)
_kaydedici = None
_konusmaci = None
_konusma_kilidi = threading.Lock()


def _kaydediciyi_al():
    global _kaydedici
    if _kaydedici is None:
        _kaydedici = stt.kaydedici_olustur()
    return _kaydedici


_wmodel = None


def _model_al():
    """Panel'den gelen ses dosyalarini cozmek icin paylasilan Whisper modeli."""
    global _wmodel
    if _wmodel is None:
        _wmodel = stt.whisper_model_yukle()
    return _wmodel


def _yanit_uret(heard: str):
    """Duyulan metni komut/beyin ile isleyip cevap ve kaynak dondurur.

    Beyne son konusmalari baglam olarak verir ve turu hafizaya kaydeder.
    """
    cevap = commands.calistir(heard)
    kaynak = "komut"
    if cevap is None:
        baglam = memory.son_baglam(config.HAFIZA_BAGLAM_ADEDI)
        cevap = brain.dusun(heard, baglam)
        kaynak = "beyin"
    memory.tur_kaydet(heard, cevap)
    return cevap, kaynak


def _konusmaciyi_al():
    global _konusmaci
    if _konusmaci is None:
        _konusmaci = tts.Konusmaci()
    return _konusmaci


def _seslendir(metin: str):
    """Cevabi arka planda seslendirir (paneli bekletmez)."""
    def _iste():
        with _konusma_kilidi:
            try:
                _konusmaciyi_al().konus(metin)
            except Exception as e:
                print("TTS hatasi:", e)
    threading.Thread(target=_iste, daemon=True).start()


# --------------------------------------------------------------------------
# Sayfalar / statik dosyalar
# --------------------------------------------------------------------------
@app.route("/")
def anasayfa():
    return send_from_directory(PANEL_KLASORU, "index.html")


@app.route("/health")
def health():
    return jsonify(ok=True)


# --------------------------------------------------------------------------
# Sesli komut akisi
# --------------------------------------------------------------------------
@app.route("/listen/start", methods=["POST"])
def listen_start():
    try:
        _kaydediciyi_al().baslat()
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.route("/listen/stop", methods=["POST"])
def listen_stop():
    try:
        heard = _kaydediciyi_al().bitir()
        print(f"[STT] duyulan: {heard!r}")
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

    if not heard:
        return jsonify(ok=True, heard="", answer="Sizi duyamadim efendim, tekrar eder misiniz?",
                       source="bos")

    # Komut/beyin isle + hafizaya kaydet (tek yerden)
    cevap, kaynak = _yanit_uret(heard)

    # Seslendirmeyi panel (tarayici) yapar; boylece sunucu sorunlarinda bile
    # hata mesajlari sesli duyulabilir ve mikrofon cakismasi olmaz.
    return jsonify(ok=True, heard=heard, answer=cevap, source=kaynak)


@app.route("/transcribe", methods=["POST"])
def transcribe():
    """Panelin tarayicida kaydettigi sesi alir, Whisper ile cozer, cevaplar."""
    f = request.files.get("audio")
    if f is None:
        return jsonify(ok=True, heard="", answer="Sizi duyamadim efendim.", source="bos")
    tmp = os.path.join(tempfile.gettempdir(), "jarvis_ses.webm")
    try:
        f.save(tmp)
        heard = stt.dosyadan_coz(_model_al(), tmp)
        print(f"[STT] duyulan: {heard!r}")
    except Exception as e:
        print("transcribe hata:", e)
        return jsonify(ok=False, error=str(e)), 500

    if not heard:
        return jsonify(ok=True, heard="", answer="Sizi duyamadim efendim, tekrar eder misiniz?",
                       source="bos")
    cevap, kaynak = _yanit_uret(heard)
    return jsonify(ok=True, heard=heard, answer=cevap, source=kaynak)


@app.route("/ask", methods=["POST"])
def ask():
    """Tarayicinin (Web Speech API) yaziya doktugu metni alir, komut/beyin ile isler.

    Yerel Whisper yerine tarayicinin cevrimici ses tanima motoru kullanildiginda
    STT tarayicida yapilir; buraya sadece cozulmus METIN gelir.
    """
    data = request.get_json(silent=True) or {}
    metin = (data.get("text") or "").strip()
    if not metin:
        return jsonify(ok=True, heard="", answer="Sizi duyamadim efendim, tekrar eder misiniz?",
                       source="bos")
    cevap, kaynak = _yanit_uret(metin)
    return jsonify(ok=True, heard=metin, answer=cevap, source=kaynak)


@app.route("/say", methods=["POST"])
def say():
    """Panelin herhangi bir metni seslendirmesi icin (ornek: BRIEF ME)."""
    data = request.get_json(silent=True) or {}
    metin = (data.get("text") or "").strip()
    if metin:
        _seslendir(metin)
    return jsonify(ok=True)


def _onisitma():
    """STT modelini arka planda onceden yukler (ilk basista gecikme olmasin)."""
    try:
        _model_al()
        print("[onisitma] STT modeli hazir.")
    except Exception as e:
        print("[onisitma] STT yuklenemedi:", e)


def main():
    print("=" * 50)
    print("  J.A.R.V.I.S panel sunucusu")
    print("  Tarayicida ac:  http://localhost:5000")
    print("=" * 50)
    threading.Thread(target=_onisitma, daemon=True).start()
    # use_reloader=False: pythonw ile tek surec calissin
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
