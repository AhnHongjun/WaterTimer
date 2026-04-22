@echo off
REM Water Timer 빌드 스크립트 (Windows)
call .venv\Scripts\activate
if exist dist rmdir /S /Q dist
if exist build rmdir /S /Q build
pyinstaller build.spec
echo.
echo 완료: dist\WaterTimer.exe
