@echo off
setlocal
echo ============================================================
echo  Zoom Attendance Server - Build Tool
echo ============================================================
echo.

REM Activar entorno virtual
call .venv\Scripts\activate.bat

REM Compilar el .exe
echo Compilando ZoomAttendanceServer.exe...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "ZoomAttendanceServer" ^
    --icon "icon.png" ^
    --add-data "icon.png;." ^
    --add-data "core.py;." ^
    --hidden-import "pystray._win32" ^
    --hidden-import "PIL._imaging" ^
    --hidden-import "uvicorn.logging" ^
    --hidden-import "uvicorn.loops" ^
    --hidden-import "uvicorn.loops.auto" ^
    --hidden-import "uvicorn.protocols" ^
    --hidden-import "uvicorn.protocols.http" ^
    --hidden-import "uvicorn.protocols.http.auto" ^
    --hidden-import "uvicorn.lifespan" ^
    --hidden-import "uvicorn.lifespan.on" ^
    server.py

echo.
if exist "dist\ZoomAttendanceServer.exe" (
    echo ============================================================
    echo  Exito! El ejecutable fue generado en:
    echo  dist\ZoomAttendanceServer.exe
    echo ============================================================
) else (
    echo [!] Error: No se genero el ejecutable. Revisa los mensajes anteriores.
)

pause
