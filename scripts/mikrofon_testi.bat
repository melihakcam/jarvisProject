@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo.
echo ==============================================
echo    JARVIS - Mikrofon (Sesli Giris) Testi
echo ==============================================
echo.
echo   1) BOSLUK tusuna BASILI TUT
echo   2) Basiliyken Turkce bir sey soyle
echo      (ornek: "Merhaba Jarvis, saat kac")
echo   3) Tusu BIRAK - konustugun yaziya donsun
echo   4) Cikmak icin  Ctrl + C
echo.
echo ----------------------------------------------
echo.
python jarvis\stt.py
echo.
echo ==============================================
echo   Test bitti. Bu pencereyi kapatabilirsin.
echo ==============================================
pause
