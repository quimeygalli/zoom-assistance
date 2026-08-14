@echo off
setlocal
echo.
echo ============================================================
echo  Zoom Attendance Tracker - Empaquetar para distribuir
echo ============================================================
echo.

set "DIST_DIR=distribucion"
set "ZIP_NAME=ZoomAttendanceTracker.zip"

REM Limpiar distribución anterior
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
mkdir "%DIST_DIR%"
mkdir "%DIST_DIR%\extension"
mkdir "%DIST_DIR%\extension\icons"

REM Copiar archivos de la extensión
copy "extension\manifest.json"   "%DIST_DIR%\extension\" > nul
copy "extension\popup.html"      "%DIST_DIR%\extension\" > nul
copy "extension\popup.js"        "%DIST_DIR%\extension\" > nul
copy "extension\icons\icon16.png"  "%DIST_DIR%\extension\icons\" > nul
copy "extension\icons\icon48.png"  "%DIST_DIR%\extension\icons\" > nul
copy "extension\icons\icon128.png" "%DIST_DIR%\extension\icons\" > nul

REM Copiar archivos para el usuario
copy "INSTRUCCIONES.txt"         "%DIST_DIR%\" > nul
copy "lista_alumnos.csv"         "%DIST_DIR%\" > nul

REM Crear el ZIP con PowerShell (disponible en Windows 10+)
echo Creando %ZIP_NAME%...
if exist "%ZIP_NAME%" del "%ZIP_NAME%"
powershell -Command "Compress-Archive -Path '%DIST_DIR%\*' -DestinationPath '%ZIP_NAME%' -Force"

if exist "%ZIP_NAME%" (
    echo.
    echo ============================================================
    echo  Listo! El archivo para distribuir fue creado:
    echo  %ZIP_NAME%
    echo ============================================================
    echo.
    echo  Compartilo por WhatsApp, Google Drive, email, etc.
    echo  El destinatario solo necesita descomprimirlo y seguir
    echo  las instrucciones del archivo INSTRUCCIONES.txt
    echo.
) else (
    echo [!] Error: No se pudo crear el ZIP.
)

pause
