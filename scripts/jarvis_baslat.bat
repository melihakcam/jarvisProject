@echo off
chcp 65001 >nul
cd /d "%~dp0.."

rem ============================================================
rem  JARVIS baslatici - HER SEY D: SURUCUSUNDE calisir.
rem  Sanal ortam, model onbellegi ve gecici dosyalar D:'de tutulur;
rem  C: surucusune hicbir sey yazilmaz.
rem ============================================================
set "VENV=D:\jarvis-env"
set "TMP=D:\jarvis-cache\tmp"
set "TEMP=D:\jarvis-cache\tmp"
set "HF_HOME=D:\jarvis-cache\hf"
set "HUGGINGFACE_HUB_CACHE=D:\jarvis-cache\hf\hub"
set "XDG_CACHE_HOME=D:\jarvis-cache"
set "PIP_CACHE_DIR=D:\jarvis-cache\pip"
if not exist "D:\jarvis-cache\tmp" mkdir "D:\jarvis-cache\tmp"
if not exist "D:\jarvis-cache\hf"  mkdir "D:\jarvis-cache\hf"

if not exist "%VENV%\Scripts\pythonw.exe" (
  echo Sanal ortam bulunamadi: %VENV%
  echo Kurmak icin:  python -m venv D:\jarvis-env
  echo sonra:        D:\jarvis-env\Scripts\pip install -r requirements.txt
  pause
  exit /b 1
)

start "" "%VENV%\Scripts\pythonw.exe" jarvis\server.py
rem Sunucu ayaga kalkana kadar bekle (en fazla ~10 sn), sonra tarayicida ac.
powershell -NoProfile -Command "for($i=0;$i -lt 20;$i++){ try{ if((Invoke-WebRequest -UseBasicParsing http://localhost:5000/health -TimeoutSec 1).StatusCode -eq 200){ break } }catch{}; Start-Sleep -Milliseconds 500 }"
start "" http://localhost:5000
exit
