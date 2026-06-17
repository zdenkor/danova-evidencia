@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==========================================
echo   Daňová evidencia - Build ZIP balíka
echo ==========================================
echo.

set VERSION=2026-06-17-0007
set ZIP_NAME=danova-evidencia-portable-%VERSION%.zip
set BUILD_DIR=build\portable

echo Čistím predchádzajúci build...
if exist build rmdir /s /q build
mkdir %BUILD_DIR%

echo Kopírujem súbory...
xcopy /s /e /i /y *.py %BUILD_DIR%\
xcopy /s /e /i /y templates %BUILD_DIR%\templates\
xcopy /s /e /i /y static %BUILD_DIR%\static\
xcopy /s /e /i /y migrations %BUILD_DIR%\migrations\
copy /y requirements.txt %BUILD_DIR%\
copy /y start.bat %BUILD_DIR%\
copy /y README.md %BUILD_DIR%\
copy /y VERSION.md %BUILD_DIR%\
copy /y DOCKER.md %BUILD_DIR%\
copy /y Dockerfile %BUILD_DIR%\
copy /y docker-compose.yml %BUILD_DIR%\

echo Vytváram .venv v balíku...
cd %BUILD_DIR%
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cd ..\..

echo Vytváram ZIP...
powershell Compress-Archive -Path %BUILD_DIR%\* -DestinationPath %ZIP_NAME% -Force

echo.
echo ==========================================
echo   Hotovo: %ZIP_NAME%
echo ==========================================
echo.
pause
