@echo off
chcp 65001 >nul
echo ==========================================
echo   Daňová evidencia - Portable
echo ==========================================
echo.

REM Nájdi Python v .venv
set PYTHON=.venv\Scripts\python.exe

if not exist %PYTHON% (
    echo CHYBA: Python nenájdený v .venv
    echo Prosím nainštalujte závislosti: pip install -r requirements.txt
    pause
    exit /b 1
)

echo Spúšťam aplikáciu...
echo Otvorte prehliadač na: http://localhost:8080
echo.
echo Pre ukončenie stlačte Ctrl+C
echo.

%PYTHON% app.py

if errorlevel 1 (
    echo.
    echo Aplikácia sa ukončila s chybou.
    pause
)
