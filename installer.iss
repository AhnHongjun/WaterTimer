; Water Timer — Inno Setup 인스톨러 스크립트
;
; 사용법:
;   1) Inno Setup 6 (무료)를 설치하세요: https://jrsoftware.org/isdl.php
;   2) `build.bat` 실행 → PyInstaller가 dist\WaterTimer.exe 를 만들고,
;      이어서 ISCC 가 이 스크립트를 컴파일해 dist\WaterTimer-Setup-X.Y.Z.exe 생성.
;
; 버전 업데이트: MyAppVersion 을 src/__init__.py 의 __version__ 과 같이 올리세요.

#define MyAppName "Water Timer"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Water Timer"
#define MyAppExeName "WaterTimer.exe"

[Setup]
; AppId 는 이 앱의 고유 식별자 — 바꾸지 마세요. 업데이트 시 같은 앱으로 인식되게 함.
AppId={{3101203A-FBF3-4774-B9E7-7203F44060F4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
; 사용자 권한으로만 설치 (관리자 권한 불필요). Chrome/VSCode 와 같은 per-user 설치 방식.
DefaultDirName={localappdata}\Programs\{#MyAppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
; 출력 파일은 dist/ 안에 저장 (PyInstaller 결과물과 같이 놓임)
OutputDir=dist
OutputBaseFilename=WaterTimer-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern
; 기존 실행 중인 WaterTimer 를 자동 종료 후 덮어쓰기 허용 (업데이트 편의)
CloseApplications=yes
RestartApplications=no
SetupIconFile=src\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면 바로가기 만들기"; GroupDescription: "추가 아이콘:"; Flags: unchecked
Name: "launchapp"; Description: "설치 완료 후 바로 실행"; GroupDescription: "설치 후:";

[Files]
Source: "dist\WaterTimer.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} 실행"; Flags: nowait postinstall skipifsilent; Tasks: launchapp

[UninstallRun]
; 언인스톨 시 Windows 자동 실행 레지스트리 항목도 정리
Filename: "reg.exe"; Parameters: "delete ""HKCU\Software\Microsoft\Windows\CurrentVersion\Run"" /v WaterTimer /f"; Flags: runhidden; RunOnceId: "RemoveRunKey"

; 주의: %APPDATA%\WaterTimer\ 안의 사용자 데이터(설정, 기록, 업로드 이미지)는 **삭제하지 않음**.
; 이는 의도된 동작 — 재설치 시 사용자 데이터가 보존되도록.
