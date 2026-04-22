# Water Timer

Windows 트레이 상주 앱. 설정한 간격마다 화면 구석에 작은 팝업을 띄워 물 마시기를 리마인드합니다.

## 사용 (비전공자용)

1. `WaterTimer.exe`를 원하는 폴더에 둔다.
2. 더블클릭으로 실행하면 작업표시줄 오른쪽 아래(트레이)에 물방울 아이콘이 뜬다.
3. 아이콘을 더블클릭하면 설정 창이 열린다.
4. 처음 한 번 "이미지 & 메시지" 탭에서 원하는 이미지/문구를 추가하면 끝.
5. 설정의 "Windows 시작 시 자동 실행"이 켜져 있으면 다음 부팅부터 자동으로 뜬다.

데이터는 `%APPDATA%\WaterTimer\`에 저장됩니다 (config.json, today.json).

## 개발 (유지보수용)

### 환경

```
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
```

(Python 3.12도 OK. Windows PowerShell에서 `.venv\Scripts\activate`가 실행 정책으로 막히면
`.venv\Scripts\python.exe`를 직접 호출해도 된다.)

### 개발 실행

```
python -m src.app
```

또는 venv를 활성화하지 않은 상태에서:

```
.venv\Scripts\python.exe -m src.app
```

### 테스트

```
pytest tests/ -v
```

### 빌드

```
build.bat
```

결과물: `dist\WaterTimer.exe` (약 40MB 단일 실행 파일)

### 문서

- 설계 스펙: `docs/superpowers/specs/2026-04-22-water-timer-design.md`
- 구현 계획: `docs/superpowers/plans/2026-04-22-water-timer-implementation.md`

## 최종 수동 QA 체크리스트

아래는 빌드한 `.exe`를 배포 전에 한 번씩 눌러봐야 하는 항목들이다. 실패 시 해당 Task로 돌아가
재점검.

- [ ] 깨끗한 Windows 사용자 계정(또는 `%APPDATA%\WaterTimer` 삭제 후)에서 .exe 첫 실행 → 에러 없이 트레이 아이콘 등장
- [ ] 실행 후 **3초 이내** 트레이 아이콘이 보임 (비기능 요구사항 §5)
- [ ] 트레이 메뉴 5항목 전부 동작 (오늘 N번 마심 / 지금 바로 알림 보기 / 일시정지 / 설정 열기 / 종료)
- [ ] 설정 4탭 전부 동작 (알림 / 이미지&메시지 / 기록 / 일반)
- [ ] 간격을 1분으로 해두고 2분 대기 → 자동 팝업 1회 뜸 (몰아치지 않음)
- [ ] "물 마셨음" → 카운터 +1, 트레이 메뉴와 기록 탭 모두 반영
- [ ] 일시정지 중에는 자동 팝업 안 뜸
- [ ] 자동 시작 ON → 재부팅 후 자동 실행 (실제 재부팅 테스트 1회)
- [ ] 두 번째 실행 시 "이미 실행 중" 메시지
- [ ] 작업 관리자에서 `WaterTimer.exe` 메모리 사용량이 **100MB 이하** 유지 (비기능 요구사항 §5)

## 오픈 이슈 (v1 마감 시점)

- **기본 번들 이미지 5장** — 현재는 placeholder 물방울 이미지. 사용자가 실제 이미지를 주면 `src/assets/bundled/img1~5.png`를 덮어쓰고 재빌드(`build.bat`)하면 된다.
- **앱 아이콘(`.ico`)** — 마찬가지로 `src/assets/icon.ico`와 `src/assets/icon.png`를 교체하고 재빌드.

## v1 스코프에서 제외한 것 (스펙 §14)

섭취량(ml), 통계·그래프, 소리 알림, 다국어, macOS/Linux, 자동 업데이트, 자정 넘는 활성 시간대 — 필요 시 별도 스펙으로 v2에서.
