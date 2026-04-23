# 배포 가이드

Water Timer 를 회사 사람·친구들에게 나눠줄 때의 표준 흐름.

## 🏁 처음 한 번 세팅 (본인이 5~15분)

### 1. Inno Setup 6 설치 (무료)

인스톨러(설치 마법사 `.exe`)를 만들어주는 도구. 한 번만 설치하면 됩니다.

1. <https://jrsoftware.org/isdl.php> 에서 **innosetup-X.X.X.exe** 다운로드
2. 그냥 설치 마법사 돌리기 (전부 기본값 OK)
3. 끝. 다음부터 `build.bat` 돌리면 인스톨러가 자동으로 같이 만들어짐

설치 후 확인: `C:\Program Files (x86)\Inno Setup 6\ISCC.exe` 가 있어야 함.

### 2. GitHub 저장소 만들기 (1회)

1. <https://github.com> 회원가입 (아직 없으면)
2. 우상단 **+** → **New repository**
3. Repository name: `water-timer` (원하는 이름)
4. **Private** 추천 (회사·친구에게만 링크로 공유). Public 해도 무방
5. "Create repository" 버튼

만들어진 화면에서 안내 명령을 복붙하거나 아래 그대로:

```
cd C:\Users\PC-55\water_timer
git remote add origin https://github.com/<본인-아이디>/water-timer.git
git branch -M main
git push -u origin main
```

첫 push 할 때 GitHub 로그인 창이 뜨면 인증. 한 번만 하면 이후 push 는 자동.

---

## 🚀 새 버전 릴리스할 때마다 (2~3분)

### 1. 빌드

```
build.bat
```

결과:
- `dist\WaterTimer.exe` — 단일 실행 파일 (압축 안 됨)
- `dist\WaterTimer-Setup-0.1.0.exe` — **사용자 배포용 인스톨러** ✨

> 버전 올릴 때는 `src\__init__.py` 의 `__version__` 과 `installer.iss` 의 `MyAppVersion` 을 같이 수정하세요. Claude 에게 "버전 X.Y.Z 로 올려줘" 하면 알아서 맞춥니다.

### 2. git 커밋 & push (제가 커밋까지 해둔 경우 스킵)

```
git push
```

### 3. GitHub Releases 에 업로드

1. GitHub 저장소 페이지 → 우측 **Releases** 클릭
2. **Draft a new release** 버튼
3. **Choose a tag** 드롭다운 → 새 태그 입력: `v0.1.0` → "Create new tag"
4. **Release title**: `v0.1.0 — 첫 배포` (마음대로)
5. **Describe this release**: 변경사항 간단히
   ```
   - 첫 공개 버전
   - 팝업 알림, 설정창, 기록·통계 기능
   ```
6. 아래 **Attach binaries** 박스에 `dist\WaterTimer-Setup-0.1.0.exe` 파일을 **드래그**
7. **Publish release** 클릭

다운로드 링크는 `https://github.com/<본인>/water-timer/releases/latest` — **이걸 공유**하시면 됩니다. 새 릴리스 낼 때마다 같은 URL 에서 자동으로 최신 인스톨러가 뜸.

---

## 👥 받는 사람 안내 문구 (복붙용)

친구·회사 분들에게 공유할 때 같이 전달하면 좋은 문구:

```
Water Timer 물 마시기 리마인더 앱입니다 💧
https://github.com/<본인>/water-timer/releases/latest

1) 위 링크에서 WaterTimer-Setup-X.X.X.exe 다운로드
2) 더블클릭 → "Windows가 PC를 보호했습니다" 파란 창이 뜨면
   '추가 정보' → '실행' 누르세요 (한 번만)
3) 설치 마법사 따라가면 끝. 트레이(작업표시줄 시계 옆)에 물방울 아이콘이 뜹니다.
4) 아이콘 더블클릭하면 설정 창. 원하는 캐릭터·메시지 고르고 알림 간격 조절하면 끝!

- 업데이트: 나중에 같은 링크에서 새 버전 받아 덮어 설치하면 설정·기록은 그대로 유지
- 문제 있으면 알려주세요
```

---

## 🧹 사용자 쪽에서 일어나는 일

- 설치 위치: `%LOCALAPPDATA%\Programs\Water Timer\WaterTimer.exe`
- 시작 메뉴 바로가기 자동 등록
- 제어판 "프로그램 추가/제거"에 뜸 → 삭제 가능
- 사용자 데이터(`config.json`, `today.json`, 업로드 이미지): `%APPDATA%\WaterTimer\` — 언인스톨 시 **보존됨** (재설치 시 자료 유지)
- Windows 시작 시 자동 실행: 설정창의 토글로 켤 수 있고, 언인스톨 시 자동 해제

## ⚠️ 알아두면 좋은 트러블슈팅

| 증상 | 원인 / 해결 |
|---|---|
| "Windows가 PC를 보호했습니다" 파란 경고 | 코드 서명 인증서가 없어서. '추가 정보' → '실행' 로 진행. 한 번 하면 끝. 반복되면 $100/년 코드 서명 인증서 구입이 유일한 해결책. |
| 친구가 "알림이 안 떠요" | `%APPDATA%\WaterTimer\error.log` 파일을 보내달라고 하세요. Claude 에게 내용 붙여넣으면 원인 진단. |
| 업데이트 설치했는데 옛날 버전으로 뜸 | 트레이에서 옛날 `.exe` 가 아직 돌고 있음. 트레이 우클릭 → 종료 → 다시 설치 또는 재실행. |
| 업데이트 후 자동 실행이 안 됨 | 설정 → 일반 → "Windows 시작 시 자동 실행" 토글을 껐다 켜기. 레지스트리 경로 갱신됨. |

---

## 🔖 버전 정책 (권장)

시맨틱 버저닝:
- **0.1.0** → **0.1.1**: 버그 수정만
- **0.1.0** → **0.2.0**: 새 기능 추가
- **0.1.0** → **1.0.0**: 안정 공개 릴리스 (첫 "정식" 버전)

지금은 `0.1.0`. 몇 번 배포해보고 안정화되면 `1.0.0` 선언.
