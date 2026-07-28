@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo JARVIS - Ses Tanima Testi
echo.
python "%~dp0ses_testi.py"
echo.
pause
