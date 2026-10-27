@echo off
chcp 65001 >nul
cd /d "%~dp0"
setlocal EnableDelayedExpansion

REM -- Leer versión del version_info.txt (línea FileVersion) --
REM Evita findstr "filevers": coincidía también con la línea
REM 'FileVersion' y la última asignación dejaba una versión rota.
set "VERSION="
for /f "tokens=4 delims='" %%v in ('findstr /i /c:"FileVersion" version_info.txt') do set "VERSION=%%v"
if not defined VERSION (
    echo Error: no pude detectar la versión en version_info.txt
    exit /b 1
)

echo Versión detectada: !VERSION!

echo Validando que existen los .exe compilados...
if not exist "dist\Optimizacion.exe" (
    echo Falta Optimizacion.exe — debe estar en dist/
    exit /b 1
)
if not exist "dist\Optimizacion-GUI.exe" (
    echo Falta Optimizacion-GUI.exe — debe estar en dist/
    exit /b 1
)
if not exist "installer\Optimizacion-Setup.exe" (
    echo Falta el instalador — debe estar en installer/
    exit /b 1
)
echo ✅ Todo existe.

echo.
echo ¿Subir a GitHub ahora? (se haría commit + push + release)
set /p RESP=Escribe SI para confirmar: 
if /i "!RESP!"=="SI" (
    git add -A
    git commit -m "v!VERSION!: automatizado con COMPILAR_Y_PUBLICAR.bat"
    git push origin main
    gh release create "v!VERSION!" dist\Optimizacion.exe dist\Optimizacion-GUI.exe installer\Optimizacion-Setup.exe --title "Optimizacion v!VERSION!" --notes-file NOTAS_RELEASE.txt --repo SaeHTs/Optimizacion-de-windows
)

pause
