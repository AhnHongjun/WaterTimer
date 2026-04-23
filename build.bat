@echo off
REM Water Timer build script (Windows)
REM 1) PyInstaller -> dist\WaterTimer.exe
REM 2) If Inno Setup 6 is installed -> dist\WaterTimer-Setup-X.Y.Z.exe

call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to activate venv at .venv\Scripts\activate.bat
    echo         Create the venv first: py -3.11 -m venv .venv
    exit /b 1
)

if exist dist rmdir /S /Q dist
if exist build rmdir /S /Q build

echo [1/2] Running PyInstaller...
pyinstaller build.spec
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller build failed. See messages above.
    exit /b 1
)

REM Detect Inno Setup compiler in standard locations
set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

if not exist "%ISCC%" (
    echo.
    echo [INFO] Inno Setup 6 not found. Installer was not built.
    echo        Install from https://jrsoftware.org/isdl.php -- it is free -- and rerun.
    echo.
    echo Done: dist\WaterTimer.exe
    exit /b 0
)

echo.
echo [2/2] Compiling Inno Setup installer...
"%ISCC%" installer.iss
if errorlevel 1 (
    echo.
    echo [ERROR] Installer compile failed.
    exit /b 1
)

echo.
echo ===== Done =====
echo   Single exe : dist\WaterTimer.exe
echo   Installer  : dist\WaterTimer-Setup-*.exe  (distribute this)
