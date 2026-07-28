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
    from jarvis import config, stt, tts, brain, commands, telemetry, weather, ajanda, eylemler
except ImportError:
    import config, stt, tts, brain, commands, telemetry, weather, ajanda, eylemler

import datetime
import os
import sys
import tempfile
import time
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
_stt_hazir = False


def _model_al():
    """Panel'den gelen ses dosyalarini cozmek icin paylasilan Whisper modeli."""
    global _wmodel, _stt_hazir
    if _wmodel is None:
        _wmodel = stt.whisper_model_yukle()
        _stt_hazir = True
    return _wmodel


# --------------------------------------------------------------------------
# Sunucu tarafi olay kaydi (panelin altindaki SISTEM KAYDI seridi)
# --------------------------------------------------------------------------
_olaylar = []
_olay_kilidi = threading.Lock()
_OLAY_SINIRI = 40


def olay(metin: str, renk: str = "rgba(160,215,240,.75)"):
    """Gercek bir olayi kayda gecirir; panel bunlari periyodik olarak ceker."""
    damga = datetime.datetime.now()
    with _olay_kilidi:
        _olaylar.append({
            "id": int(damga.timestamp() * 1000) + len(_olaylar),
            "line": f"[{damga.strftime('%H:%M:%S')}] {metin}",
            "color": renk,
        })
        del _olaylar[:-_OLAY_SINIRI]
    print("[olay]", metin)


def _yanit_uret(heard: str):
    """Duyulan metni hatirlatici/komut/beyin sirasiyla isleyip cevap dondurur."""
    olay("sen: " + heard, "#a8e2fa")

    # 1) Hatirlatici kurma istegi mi? ("15:00'te toplanti hatirlat")
    hatirlatici = ajanda.komuttan_ekle(heard)
    if hatirlatici is not None:
        if hatirlatici.get("ok"):
            k = hatirlatici["kayit"]
            olay(f"hatırlatıcı kuruldu — {k['time']} {k['title']}", "#6effc0")
        return hatirlatici["answer"], "ajanda"

    # 2) Yerel bilgisayar komutu mu?
    cevap = commands.calistir(heard)
    kaynak = "komut"
    # 3) Degilse beyne sor
    if cevap is None:
        cevap = brain.dusun(heard)
        kaynak = "beyin"
    olay(f"jarvis yanıtladı ({kaynak}).", "#6effc0")
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


@app.route("/say", methods=["POST"])
def say():
    """Panelin herhangi bir metni seslendirmesi icin (ornek: BRIEF ME)."""
    data = request.get_json(silent=True) or {}
    metin = (data.get("text") or "").strip()
    if metin:
        _seslendir(metin)
    return jsonify(ok=True)


# --------------------------------------------------------------------------
# Gercek veri uclari (panelin tum kartlari bunlardan beslenir)
# --------------------------------------------------------------------------
@app.route("/api/telemetry")
def api_telemetry():
    """Yasam belirtileri, ag trafigi, baglanti durumlari ve uyarilar."""
    yaklasan = ajanda.yaklasan(60)
    satirlar, ozet = telemetry.baglantilar(stt_hazir=_stt_hazir)
    return jsonify(
        vitals=telemetry.vitals(),
        net=telemetry.ag(),
        links=satirlar,
        linkSummary=ozet,
        alerts=telemetry.uyarilar(yaklasan),
        host=telemetry.bilgisayar_adi(),
        focus=eylemler.odak_durumu(),
        backup=eylemler.son_yedek(),
        stt=_stt_hazir,
        brain=telemetry.beyin_var(),
    )


@app.route("/api/weather")
def api_weather():
    return jsonify(weather.hava())


@app.route("/api/agenda", methods=["GET", "POST"])
def api_agenda():
    if request.method == "POST":
        d = request.get_json(silent=True) or {}
        baslik = (d.get("title") or "").strip()
        saat = (d.get("time") or "").strip()
        if not baslik or not saat:
            return jsonify(ok=False, error="Saat ve başlık gerekli."), 400
        kayit = ajanda.ekle(saat, baslik, d.get("meta") or "PANEL",
                            d.get("date"))
        olay(f"ajandaya eklendi — {kayit['time']} {kayit['title']}", "#6effc0")
        return jsonify(ok=True, item=kayit, items=ajanda.liste())
    return jsonify(ok=True, items=ajanda.liste(), upcoming=ajanda.yaklasan(60))


@app.route("/api/agenda/<kayit_id>", methods=["DELETE"])
def api_agenda_sil(kayit_id):
    silindi = ajanda.sil(kayit_id)
    if silindi:
        olay("ajanda kaydı silindi.", "#ffc689")
    return jsonify(ok=silindi, items=ajanda.liste())


@app.route("/api/logs")
def api_logs():
    """Panelin sistem kaydi seridi: sadece gercek olaylar."""
    try:
        sonra = int(request.args.get("after", 0))
    except ValueError:
        sonra = 0
    with _olay_kilidi:
        yeni = [o for o in _olaylar if o["id"] > sonra]
    return jsonify(ok=True, events=yeni)


@app.route("/api/brief", methods=["POST"])
def api_brief():
    """Gercek verilerden brifing uretir ve sesli okur."""
    metin = eylemler.brifing()
    olay("brifing derlendi — hava, ajanda ve sistem durumu.", "#6effc0")
    return jsonify(ok=True, text=metin)


@app.route("/api/action/<ad>", methods=["POST"])
def api_action(ad):
    """Hizli komut butonlari: hepsi gercek bir islem yapar."""
    if ad == "brifing":
        metin = eylemler.brifing()
        olay("brifing derlendi — hava, ajanda ve sistem durumu.", "#6effc0")
        return jsonify(ok=True, answer=metin)

    islev = eylemler.EYLEMLER.get(ad)
    if islev is None:
        return jsonify(ok=False, error="Bilinmeyen eylem"), 404

    d = request.get_json(silent=True) or {}
    sonuc = islev(d["state"]) if (ad == "odak" and "state" in d) else islev()
    olay(sonuc.get("log", ad), "#6effc0" if sonuc.get("ok") else "#ffb35c")
    return jsonify(sonuc)


# --------------------------------------------------------------------------
# Hatirlatici bekcisi: saati gelen kaydi gercekten sesli soyler
# --------------------------------------------------------------------------
def _hatirlatici_dongusu():
    while True:
        try:
            for k in ajanda.zamani_gelenler():
                metin = f"Hatırlatma efendim: saat {k['time']}, {k['title']}."
                olay(f"hatırlatıcı çaldı — {k['time']} {k['title']}", "#ffb35c")
                _seslendir(metin)
        except Exception as e:
            print("hatirlatici hatasi:", e)
        time.sleep(20)


def _onisitma():
    """STT modelini arka planda onceden yukler (ilk basista gecikme olmasin)."""
    try:
        _model_al()
        print("[onisitma] STT modeli hazir.")
        olay("ses tanıma motoru yüklendi — mikrofon hazır.", "#6effc0")
    except Exception as e:
        print("[onisitma] STT yuklenemedi:", e)
        olay(f"ses tanıma yüklenemedi: {e}", "#ffb35c")


def main():
    print("=" * 50)
    print("  J.A.R.V.I.S panel sunucusu")
    print("  Tarayicida ac:  http://localhost:5000")
    print("=" * 50)
    telemetry.baslat()
    olay(f"sistem çevrimiçi — {telemetry.bilgisayar_adi()} üzerinde başlatıldı.", "#6effc0")
    threading.Thread(target=_onisitma, daemon=True).start()
    threading.Thread(target=_hatirlatici_dongusu, daemon=True).start()
    # use_reloader=False: pythonw ile tek surec calissin
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
