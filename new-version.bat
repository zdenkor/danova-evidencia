@echo off
chcp 65001 >nul
:: Skript na vytvorenie novej verzie
:: Použitie: new-version.bat "Popis zmien"

setlocal EnableDelayedExpansion

if "%~1"=="" (
    echo Použitie: new-version.bat "Popis zmien"
    echo Príklad: new-version.bat "Oprava chyby v exporte"
    exit /b 1
)

set "POPIS=%~1"
set "DATUM=%date:~-4%-%date:~3,2%-%date:~0,2%"

:: Získaj posledné poradové číslo z git tagov
for /f "tokens=*" %%a in ('git tag --sort=-v:refname 2^>nul') do (
    set "LAST_TAG=%%a"
    goto :found_tag
)

:: Ak nie sú žiadne tagy, začni od 0001
set "NOVE_CISLO=0001"
goto :create_version

:found_tag
:: Extrahuj posledné 4 číslice z tagu
set "LAST_NUM=!LAST_TAG:~-4!"
:: Odstráň leading zeros pre aritmetiku
set /a LAST_NUM=10000!LAST_NUM! %% 10000
set /a NOVE_CISLO=LAST_NUM + 1

:: Formátuj s leading zeros
if !NOVE_CISLO! LSS 10 (
    set "NOVE_CISLO=000!NOVE_CISLO!"
) else if !NOVE_CISLO! LSS 100 (
    set "NOVE_CISLO=00!NOVE_CISLO!"
) else if !NOVE_CISLO! LSS 1000 (
    set "NOVE_CISLO=0!NOVE_CISLO!"
) else (
    set "NOVE_CISLO=!NOVE_CISLO!"
)

:create_version
set "VERZIA=%DATUM%-%NOVE_CISLO%"
set "TAG=v%VERZIA%"

echo ========================================
echo Vytváram novú verziu: %VERZIA%
echo ========================================

:: Pridaj záznam do VERSION.md
echo. >> VERSION.md
echo --- >> VERSION.md
echo. >> VERSION.md
echo ## %VERZIA% >> VERSION.md
echo. >> VERSION.md
echo ### Zmeny >> VERSION.md
echo - %POPIS% >> VERSION.md

git add VERSION.md
git commit -m "Release %VERZIA%

%POPIS%"
git tag -a "%TAG%" -m "Version %VERZIA%: %POPIS%"
git push origin master --tags

echo.
echo ✓ Verzia %VERZIA% bola vytvorená a pushnutá!
echo   Tag: %TAG%
echo.
pause
