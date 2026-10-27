@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM ============================================================
REM  Publicar nueva versión en GitHub Releases
REM  Uso: SUBIR_RELEASE.bat <version>   (ej: SUBIR_RELEASE.bat 1.8.2)
REM  Si no pasas versión, se usa la de version_info.txt
REM ============================================================

REM --- Localizar gh.exe sin rutas de usuario hardcodeadas ---
set "GH=gh.exe"
where /q gh.exe
if errorlevel 1 set "GH=C:\Program Files\GitHub CLI\gh.exe"
if not exist "%GH%" set "GH=%LOCALAPPDATA%\Programs\GitHub CLI\gh.exe"

REM --- Versión: argumento o la de version_info.txt (línea FileVersion) ---
REM Evita findstr "filevers": coincidía también con la línea
REM 'FileVersion' y la última asignación dejaba una versión rota.
set "VERSION=%~1"
if not defined VERSION (
    for /f "tokens=4 delims='" %%v in ('findstr /i /c:"FileVersion" version_info.txt') do set "VERSION=%%v"
)
if not defined VERSION (
    echo ❌ No se pudo detectar la versión. Uso: SUBIR_RELEASE.bat ^<versión^>
    exit /b 1
)

set "TAG=v%VERSION%"

echo ====================================================
echo   Publicando Optimizacion %TAG% en GitHub Releases
echo ====================================================
echo.

REM --- Verificar que existen los ejecutables ---
if not exist "dist\Optimizacion.exe" (
    echo ❌ Falta dist\Optimizacion.exe — compilalo primero
    exit /b 1
)
if not exist "dist\Optimizacion-GUI.exe" (
    echo ❌ Falta dist\Optimizacion-GUI.exe — compilalo primero
    exit /b 1
)
if not exist "installer\Optimizacion-Setup.exe" (
    echo ❌ Falta installer\Optimizacion-Setup.exe — compilalo primero
    exit /b 1
)

REM --- Login con GitHub CLI la primera vez ---
"%GH%" auth status >nul 2>&1
if errorlevel 1 (
    echo Abriendo navegador para iniciar sesión en GitHub...
    "%GH%" auth login --web --git-protocol https
)

echo.
echo Subiendo release %TAG%...
echo   - dist\Optimizacion.exe
echo   - dist\Optimizacion-GUI.exe
echo   - installer\Optimizacion-Setup.exe
echo.

"%GH%" release create %TAG% dist\Optimizacion.exe dist\Optimizacion-GUI.exe installer\Optimizacion-Setup.exe --title "Optimizacion %TAG%" --notes "Nueva versión del optimizador. Ver https://github.com/SaeHTs/Optimizacion-de-windows#readme para novedades." --repo SaeHTs/Optimizacion-de-windows

if errorlevel 1 (
    echo.
    echo ❌ Falla al publicar. Revisa el error arriba.
) else (
    echo.
    echo ✅ Publicado: https://github.com/SaeHTs/Optimizacion-de-windows/releases/tag/%TAG%
)

pause
