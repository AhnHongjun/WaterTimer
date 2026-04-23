@echo off
REM Water Timer 빌드 스크립트 (Windows)
REM 1) PyInstaller 로 dist\WaterTimer.exe 생성
REM 2) Inno Setup 이 설치돼 있으면 dist\WaterTimer-Setup-X.Y.Z.exe 도 생성

call .venv\Scripts\activate
if exist dist rmdir /S /Q dist
if exist build rmdir /S /Q build

echo [1/2] PyInstaller 실행 중...
pyinstaller build.spec
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller 빌드 실패. 위 메시지를 확인하세요.
    exit /b 1
)

REM Inno Setup 컴파일러 경로 탐지 (표준 설치 위치)
set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

if not exist "%ISCC%" (
    echo.
    echo [INFO] Inno Setup 6 이 설치되지 않아 인스톨러는 만들지 않습니다.
    echo        설치 후 다시 실행하면 WaterTimer-Setup-X.Y.Z.exe 가 생성됩니다.
    echo        다운로드: https://jrsoftware.org/isdl.php  (무료)
    echo.
    echo 완료: dist\WaterTimer.exe
    exit /b 0
)

echo.
echo [2/2] Inno Setup 인스톨러 컴파일 중...
"%ISCC%" installer.iss
if errorlevel 1 (
    echo.
    echo [ERROR] 인스톨러 컴파일 실패.
    exit /b 1
)

echo.
echo ===== 완료 =====
echo   - 단일 실행파일 : dist\WaterTimer.exe
echo   - 설치 프로그램 : dist\WaterTimer-Setup-*.exe  (배포용)
