@echo off
chcp 65001 >nul
cd /d "%~dp0.."
rem JARVIS panelini baslatir: sunucuyu penceresiz calistirir, hazir olunca paneli acar.
start "" pythonw jarvis\server.py
rem Sunucu ayaga kalkana kadar bekle (en fazla ~10 sn), sonra tarayicida ac.
powershell -NoProfile -Command "for($i=0;$i -lt 20;$i++){ try{ if((Invoke-WebRequest -UseBasicParsing http://localhost:5000/health -TimeoutSec 1).StatusCode -eq 200){ break } }catch{}; Start-Sleep -Milliseconds 500 }"
start "" http://localhost:5000
exit
