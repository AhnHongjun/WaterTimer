# Water Timer 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Windows 트레이 상주 앱으로, 설정한 간격마다 화면 구석에 이미지+메시지+'물 마셨음' 버튼 팝업을 띄우는 MVP → 설정 창 → 시스템 통합 → 단일 .exe 배포까지 완성.

**Architecture:** 순수 로직(`config`, `state`, `scheduler`, `autostart`)은 PySide6 의존 없이 TDD로 검증. UI(`popup`, `tray`, `settings_window`)는 얇은 껍데기로 유지하고 수동 테스트. `app.py`가 모든 조각을 연결하는 유일한 지점. 설정은 `%APPDATA%\WaterTimer\config.json`, 런타임 상태는 `today.json`에 JSON으로 저장.

**Tech Stack:** Python 3.11+, PySide6 6.6+, pytest, freezegun(시간 모킹), PyInstaller 6.x. Windows 10/11 x64 전용.

---

## 파일 구조 (최종)

```
water_timer/
├── src/
│   ├── __init__.py
│   ├── paths.py            # %APPDATA% 경로 상수
│   ├── config.py           # config.json 스키마·로드·저장·기본값
│   ├── state.py            # today.json (count, date, last_notified_at)
│   ├── scheduler.py        # 순수 판정 로직 (should_fire, select_set)
│   ├── popup.py            # 알림 팝업 QWidget
│   ├── tray.py             # QSystemTrayIcon + 우클릭 메뉴
│   ├── settings_window.py  # 설정 QDialog + 4개 탭
│   ├── autostart.py        # Windows 레지스트리 Run 키
│   ├── single_instance.py  # 뮤텍스 중복 실행 방지
│   ├── error_log.py        # 로깅 설정 + 글로벌 예외 훅
│   ├── app.py              # 진입점
│   └── assets/
│       ├── icon.ico
│       └── bundled/        # 기본 이미지 5장 (placeholder → 실제 교체)
├── tests/
│   ├── __init__.py
│   ├── test_paths.py
│   ├── test_config.py
│   ├── test_state.py
│   ├── test_scheduler.py
│   └── test_autostart.py
├── requirements.txt
├── requirements-dev.txt
├── .gitignore
├── build.spec              # PyInstaller 설정
├── build.bat               # 빌드 단축 스크립트
└── docs/superpowers/{specs,plans}/...
```

**책임 분리 원칙**:
- `config.py` = 사용자가 바꾸는 값(간격, 세트 등)
- `state.py` = 앱이 기록하는 런타임 상태(카운터, 마지막 알림 시각)
- `scheduler.py` = 순수 함수. 외부 의존 0. 테스트 쉬움
- UI 모듈들은 상태를 직접 갖지 않음. 콜백과 데이터만 받음

---

# Phase 1 — MVP (트레이 + 타이머 + 팝업)

Phase 1이 끝나면 사용자는 `python src/app.py`로 실행해서 트레이 아이콘을 보고, "지금 바로 알림 보기" 메뉴로 팝업 외형을 확인할 수 있다.

## Task 1: 프로젝트 초기 셋업

**Files:**
- Create: `C:\Users\PC-55\water_timer\.gitignore`
- Create: `C:\Users\PC-55\water_timer\requirements.txt`
- Create: `C:\Users\PC-55\water_timer\requirements-dev.txt`
- Create: `C:\Users\PC-55\water_timer\src\__init__.py`
- Create: `C:\Users\PC-55\water_timer\tests\__init__.py`
- Create: `C:\Users\PC-55\water_timer\src\assets\bundled\.gitkeep`

- [ ] **Step 1: `.gitignore` 작성**

파일: `C:\Users\PC-55\water_timer\.gitignore`
```
# Python
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.venv/
venv/
*.egg-info/

# PyInstaller
build/
dist/
*.manifest

# IDE
.vscode/
.idea/

# OS
Thumbs.db
desktop.ini

# Local secrets / scratch
.env
scratch/
```

- [ ] **Step 2: `requirements.txt` (런타임 의존성)**

파일: `C:\Users\PC-55\water_timer\requirements.txt`
```
PySide6==6.6.3
```

- [ ] **Step 3: `requirements-dev.txt` (개발·빌드·테스트 의존성)**

파일: `C:\Users\PC-55\water_timer\requirements-dev.txt`
```
-r requirements.txt
pytest==8.2.0
freezegun==1.5.1
pyinstaller==6.6.0
```

- [ ] **Step 4: 빈 `__init__.py` 2개 생성**

파일: `C:\Users\PC-55\water_timer\src\__init__.py` — 빈 파일 (0 bytes)
파일: `C:\Users\PC-55\water_timer\tests\__init__.py` — 빈 파일 (0 bytes)

- [ ] **Step 5: `src/assets/bundled/.gitkeep` 생성**

파일: `C:\Users\PC-55\water_timer\src\assets\bundled\.gitkeep` — 빈 파일 (빈 디렉터리를 git에 추적시키기 위한 관례)

- [ ] **Step 6: 가상환경 생성 및 의존성 설치**

Windows PowerShell에서 실행:
```
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

실행 후 기대 결과: `.venv\` 폴더 생성, `pip list`에서 PySide6, pytest, freezegun, pyinstaller 확인 가능.

- [ ] **Step 7: pytest 스모크 실행 (테스트 0개 정상)**

```
pytest tests/ -v
```
기대 결과: `no tests ran in X.XXs` — 에러 없이 종료.

- [ ] **Step 8: 커밋**

```
git add .gitignore requirements.txt requirements-dev.txt src/ tests/
git commit -m "chore: scaffold project structure and dependencies"
```

---

## Task 2: `paths.py` — 사용자 데이터 경로

**Files:**
- Create: `src/paths.py`
- Create: `tests/test_paths.py`

- [ ] **Step 1: 실패하는 테스트 작성**

파일: `C:\Users\PC-55\water_timer\tests\test_paths.py`
```python
from pathlib import Path
import os
from src import paths


def test_app_data_dir_creates_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    result = paths.app_data_dir()
    assert result == tmp_path / "WaterTimer"
    assert result.is_dir()


def test_config_path_points_to_config_json(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert paths.config_path() == tmp_path / "WaterTimer" / "config.json"


def test_state_path_points_to_today_json(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert paths.state_path() == tmp_path / "WaterTimer" / "today.json"


def test_error_log_path_points_to_error_log(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert paths.error_log_path() == tmp_path / "WaterTimer" / "error.log"
```

- [ ] **Step 2: 테스트 실패 확인**

```
pytest tests/test_paths.py -v
```
기대 결과: 4개 모두 FAIL — `ModuleNotFoundError: No module named 'src.paths'`.

- [ ] **Step 3: `src/paths.py` 구현**

파일: `C:\Users\PC-55\water_timer\src\paths.py`
```python
"""%APPDATA%\WaterTimer 경로 모음. 없으면 자동 생성."""
from pathlib import Path
import os

APP_NAME = "WaterTimer"


def app_data_dir() -> Path:
    appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    path = Path(appdata) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return app_data_dir() / "config.json"


def state_path() -> Path:
    return app_data_dir() / "today.json"


def error_log_path() -> Path:
    return app_data_dir() / "error.log"
```

- [ ] **Step 4: 테스트 통과 확인**

```
pytest tests/test_paths.py -v
```
기대 결과: 4 PASS.

- [ ] **Step 5: 커밋**

```
git add src/paths.py tests/test_paths.py
git commit -m "feat(paths): add AppData directory helpers with tests"
```

---

## Task 3: `state.py` — 런타임 상태 (today.json)

**Files:**
- Create: `src/state.py`
- Create: `tests/test_state.py`

today.json 스키마:
```json
{"date": "2026-04-22", "count": 5, "last_notified_at": "2026-04-22T14:30:00"}
```
`last_notified_at`은 null 가능. `date`는 로컬 타임존 날짜.

- [ ] **Step 1: 실패하는 테스트 작성**

파일: `C:\Users\PC-55\water_timer\tests\test_state.py`
```python
import json
from datetime import datetime
from pathlib import Path

import pytest
from freezegun import freeze_time

from src import state


@pytest.fixture
def state_file(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path / "WaterTimer" / "today.json"


@freeze_time("2026-04-22 10:00:00")
def test_load_creates_default_when_missing(state_file):
    s = state.load()
    assert s.date == "2026-04-22"
    assert s.count == 0
    assert s.last_notified_at is None


@freeze_time("2026-04-22 10:00:00")
def test_save_then_load_roundtrip(state_file):
    s = state.State(date="2026-04-22", count=3,
                    last_notified_at=datetime(2026, 4, 22, 9, 30))
    state.save(s)
    loaded = state.load()
    assert loaded.count == 3
    assert loaded.last_notified_at == datetime(2026, 4, 22, 9, 30)


@freeze_time("2026-04-23 01:00:00")
def test_load_resets_when_date_changed(state_file):
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({
        "date": "2026-04-22", "count": 7,
        "last_notified_at": "2026-04-22T22:00:00"
    }))
    s = state.load()
    assert s.date == "2026-04-23"
    assert s.count == 0
    assert s.last_notified_at is None  # 날짜 바뀌면 마지막 알림도 초기화


@freeze_time("2026-04-22 10:00:00")
def test_increment_count(state_file):
    s = state.load()
    s2 = state.increment_count(s)
    assert s2.count == 1
    assert state.load().count == 1


@freeze_time("2026-04-22 10:00:00")
def test_update_last_notified(state_file):
    s = state.load()
    now = datetime(2026, 4, 22, 10, 0)
    s2 = state.update_last_notified(s, now)
    assert s2.last_notified_at == now
    assert state.load().last_notified_at == now


@freeze_time("2026-04-22 10:00:00")
def test_corrupted_file_recovers_to_default_and_backs_up(state_file):
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text("{not valid json")
    s = state.load()
    assert s.count == 0
    assert state_file.with_suffix(".json.bak").exists()
```

- [ ] **Step 2: 테스트 실패 확인**

```
pytest tests/test_state.py -v
```
기대: 6개 FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: `src/state.py` 구현**

파일: `C:\Users\PC-55\water_timer\src\state.py`
```python
"""today.json — 오늘의 카운터 + 마지막 알림 시각.

날짜가 바뀌면 load() 시점에 자동으로 리셋된다.
파일이 손상되면 기본값으로 복구하고 손상본을 .bak으로 백업한다.
"""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime, date
from typing import Optional

from src import paths


@dataclass
class State:
    date: str                                # "YYYY-MM-DD"
    count: int
    last_notified_at: Optional[datetime]     # None 또는 datetime


def _today_str() -> str:
    return date.today().isoformat()


def _default() -> State:
    return State(date=_today_str(), count=0, last_notified_at=None)


def _to_dict(s: State) -> dict:
    d = asdict(s)
    d["last_notified_at"] = s.last_notified_at.isoformat() if s.last_notified_at else None
    return d


def _from_dict(d: dict) -> State:
    last = d.get("last_notified_at")
    return State(
        date=d["date"],
        count=int(d["count"]),
        last_notified_at=datetime.fromisoformat(last) if last else None,
    )


def load() -> State:
    path = paths.state_path()
    if not path.exists():
        s = _default()
        save(s)
        return s
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        loaded = _from_dict(data)
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        shutil.copy2(path, path.with_suffix(".json.bak"))
        s = _default()
        save(s)
        return s
    # 날짜 전환 처리
    if loaded.date != _today_str():
        s = _default()
        save(s)
        return s
    return loaded


def save(s: State) -> None:
    path = paths.state_path()
    path.write_text(json.dumps(_to_dict(s), ensure_ascii=False, indent=2), encoding="utf-8")


def increment_count(s: State) -> State:
    s2 = State(date=s.date, count=s.count + 1, last_notified_at=s.last_notified_at)
    save(s2)
    return s2


def update_last_notified(s: State, when: datetime) -> State:
    s2 = State(date=s.date, count=s.count, last_notified_at=when)
    save(s2)
    return s2
```

- [ ] **Step 4: 테스트 통과 확인**

```
pytest tests/test_state.py -v
```
기대: 6 PASS.

- [ ] **Step 5: 커밋**

```
git add src/state.py tests/test_state.py
git commit -m "feat(state): add today.json with date-rollover and corruption recovery"
```

---

## Task 4: `config.py` — 사용자 설정 (config.json)

**Files:**
- Create: `src/config.py`
- Create: `tests/test_config.py`

config.json 스키마:
```json
{
  "interval_minutes": 60,
  "active_start": "09:00",
  "active_end": "22:00",
  "popup_position": "bottom_right",
  "auto_close_seconds": 12,
  "autostart": true,
  "sets": [
    {"id": "s1", "image_path": "<bundled>/img1.png", "message": "물 한 잔 어때요? 💧"},
    ...
  ]
}
```

제약:
- `interval_minutes` ∈ [1, 1440]
- `auto_close_seconds` ∈ [3, 60]
- `popup_position` ∈ {"bottom_right","bottom_left","top_right","top_left","center"}
- `active_start` < `active_end` (HH:MM, 둘 다 "00:00"~"23:59")
- 손상/누락 시 기본값으로 자동 복구, 손상본은 `.bak`

`<bundled>` 접두사는 런타임에 앱 설치 폴더로 치환된다 (Task 6에서 다룸).

- [ ] **Step 1: 실패하는 테스트 작성**

파일: `C:\Users\PC-55\water_timer\tests\test_config.py`
```python
import json

import pytest

from src import config


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path / "WaterTimer" / "config.json"


def test_load_creates_default_when_missing(config_file):
    c = config.load()
    assert c.interval_minutes == 60
    assert c.active_start == "09:00"
    assert c.active_end == "22:00"
    assert c.popup_position == "bottom_right"
    assert c.auto_close_seconds == 12
    assert c.autostart is True
    assert len(c.sets) == 5
    assert c.sets[0].message == "물 한 잔 어때요? 💧"
    assert config_file.exists()


def test_save_then_load_roundtrip(config_file):
    c = config.load()
    c2 = config.replace(c, interval_minutes=30, active_start="08:00")
    config.save(c2)
    loaded = config.load()
    assert loaded.interval_minutes == 30
    assert loaded.active_start == "08:00"


def test_corrupted_file_recovers_and_backs_up(config_file):
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text("{broken")
    c = config.load()
    assert c.interval_minutes == 60
    assert config_file.with_suffix(".json.bak").exists()


@pytest.mark.parametrize("minutes", [0, -5, 1441, 99999])
def test_invalid_interval_rejected(minutes):
    with pytest.raises(ValueError):
        config.validate_interval_minutes(minutes)


@pytest.mark.parametrize("minutes", [1, 60, 1440])
def test_valid_interval_accepted(minutes):
    config.validate_interval_minutes(minutes)  # no raise


def test_active_start_must_be_before_end():
    with pytest.raises(ValueError):
        config.validate_active_window("22:00", "09:00")


def test_active_window_equal_rejected():
    with pytest.raises(ValueError):
        config.validate_active_window("09:00", "09:00")


def test_active_window_valid():
    config.validate_active_window("09:00", "22:00")


def test_invalid_position_rejected():
    with pytest.raises(ValueError):
        config.validate_position("diagonal")


def test_valid_positions():
    for p in ["bottom_right", "bottom_left", "top_right", "top_left", "center"]:
        config.validate_position(p)


def test_add_remove_update_set(config_file):
    c = config.load()
    new_set = config.Set(id="new", image_path="C:/x.png", message="hi")
    c2 = config.add_set(c, new_set)
    assert len(c2.sets) == 6
    assert c2.sets[-1].id == "new"

    c3 = config.update_set(c2, "new", image_path="C:/y.png", message="bye")
    assert c3.sets[-1].image_path == "C:/y.png"
    assert c3.sets[-1].message == "bye"

    c4 = config.remove_set(c3, "new")
    assert len(c4.sets) == 5
```

- [ ] **Step 2: 테스트 실패 확인**

```
pytest tests/test_config.py -v
```
기대: 다수 FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: `src/config.py` 구현**

파일: `C:\Users\PC-55\water_timer\src\config.py`
```python
"""config.json — 사용자 설정.

스키마 변경 시: DEFAULT_CONFIG 업데이트 + migration 코드 추가.
손상/누락 시 자동 복구 + .bak 백업.
"""
from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass, asdict, replace as dc_replace
from typing import List, Optional

from src import paths


VALID_POSITIONS = {"bottom_right", "bottom_left", "top_right", "top_left", "center"}
MIN_INTERVAL = 1
MAX_INTERVAL = 1440       # 24h
MIN_AUTO_CLOSE = 3
MAX_AUTO_CLOSE = 60

BUNDLED_PREFIX = "<bundled>"  # 런타임에 앱 설치 폴더로 치환

DEFAULT_MESSAGES = [
    "물 한 잔 어때요? 💧",
    "목마르지 않아도 마셔야 해요",
    "잠깐, 물 한 모금!",
    "오늘도 수고했어요. 물 한 잔 하고 가요",
    "탈수는 소리 없이 와요",
]


@dataclass(frozen=True)
class Set:
    id: str
    image_path: str   # "<bundled>/img1.png" 또는 절대 경로
    message: str


@dataclass(frozen=True)
class Config:
    interval_minutes: int
    active_start: str           # "HH:MM"
    active_end: str             # "HH:MM"
    popup_position: str
    auto_close_seconds: int
    autostart: bool
    sets: List[Set]


def _default() -> Config:
    sets = [
        Set(id=f"default_{i+1}",
            image_path=f"{BUNDLED_PREFIX}/img{i+1}.png",
            message=msg)
        for i, msg in enumerate(DEFAULT_MESSAGES)
    ]
    return Config(
        interval_minutes=60,
        active_start="09:00",
        active_end="22:00",
        popup_position="bottom_right",
        auto_close_seconds=12,
        autostart=True,
        sets=sets,
    )


# ---------- validation ----------

def validate_interval_minutes(m: int) -> None:
    if not isinstance(m, int) or m < MIN_INTERVAL or m > MAX_INTERVAL:
        raise ValueError(f"간격은 {MIN_INTERVAL}~{MAX_INTERVAL}분 사이여야 합니다")


def validate_auto_close(s: int) -> None:
    if not isinstance(s, int) or s < MIN_AUTO_CLOSE or s > MAX_AUTO_CLOSE:
        raise ValueError(f"자동 닫힘은 {MIN_AUTO_CLOSE}~{MAX_AUTO_CLOSE}초 사이여야 합니다")


def validate_position(p: str) -> None:
    if p not in VALID_POSITIONS:
        raise ValueError(f"지원하지 않는 위치: {p}")


def _parse_hhmm(s: str) -> int:
    """'HH:MM' → 분 단위 정수. 잘못된 형식이면 ValueError."""
    parts = s.split(":")
    if len(parts) != 2:
        raise ValueError(f"시간 형식 오류: {s}")
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"시간 범위 오류: {s}")
    return h * 60 + m


def validate_active_window(start: str, end: str) -> None:
    s, e = _parse_hhmm(start), _parse_hhmm(end)
    if s >= e:
        raise ValueError("활성 시작 시각은 종료 시각보다 빨라야 합니다")


# ---------- IO ----------

def _to_dict(c: Config) -> dict:
    d = asdict(c)
    d["sets"] = [asdict(s) for s in c.sets]
    return d


def _from_dict(d: dict) -> Config:
    sets = [Set(**s) for s in d.get("sets", [])]
    return Config(
        interval_minutes=int(d["interval_minutes"]),
        active_start=str(d["active_start"]),
        active_end=str(d["active_end"]),
        popup_position=str(d["popup_position"]),
        auto_close_seconds=int(d["auto_close_seconds"]),
        autostart=bool(d["autostart"]),
        sets=sets,
    )


def _validate(c: Config) -> None:
    validate_interval_minutes(c.interval_minutes)
    validate_auto_close(c.auto_close_seconds)
    validate_position(c.popup_position)
    validate_active_window(c.active_start, c.active_end)


def load() -> Config:
    path = paths.config_path()
    if not path.exists():
        c = _default()
        save(c)
        return c
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        c = _from_dict(data)
        _validate(c)
        return c
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        shutil.copy2(path, path.with_suffix(".json.bak"))
        c = _default()
        save(c)
        return c


def save(c: Config) -> None:
    _validate(c)
    path = paths.config_path()
    path.write_text(json.dumps(_to_dict(c), ensure_ascii=False, indent=2), encoding="utf-8")


# ---------- mutation helpers (순수) ----------

def replace(c: Config, **changes) -> Config:
    return dc_replace(c, **changes)


def new_set_id() -> str:
    return f"set_{uuid.uuid4().hex[:8]}"


def add_set(c: Config, s: Set) -> Config:
    return dc_replace(c, sets=c.sets + [s])


def remove_set(c: Config, set_id: str) -> Config:
    return dc_replace(c, sets=[s for s in c.sets if s.id != set_id])


def update_set(c: Config, set_id: str, *,
               image_path: Optional[str] = None,
               message: Optional[str] = None) -> Config:
    new_sets = []
    for s in c.sets:
        if s.id == set_id:
            new_sets.append(Set(
                id=s.id,
                image_path=image_path if image_path is not None else s.image_path,
                message=message if message is not None else s.message,
            ))
        else:
            new_sets.append(s)
    return dc_replace(c, sets=new_sets)
```

- [ ] **Step 4: 테스트 통과 확인**

```
pytest tests/test_config.py -v
```
기대: 전 항목 PASS.

- [ ] **Step 5: 커밋**

```
git add src/config.py tests/test_config.py
git commit -m "feat(config): add config.json schema, validation, and CRUD helpers"
```

---

## Task 5: `scheduler.py` — 순수 판정 로직

**Files:**
- Create: `src/scheduler.py`
- Create: `tests/test_scheduler.py`

scheduler는 **Qt 의존 0**. 타이머는 `app.py`가 관리하고, scheduler는 "이 시점에 발사할지 / 어떤 세트를 고를지"만 판정한다.

- [ ] **Step 1: 실패하는 테스트 작성**

파일: `C:\Users\PC-55\water_timer\tests\test_scheduler.py`
```python
from datetime import datetime

import pytest

from src import scheduler
from src.config import Config, Set
from src.state import State


def make_config(**overrides):
    base = dict(
        interval_minutes=60,
        active_start="09:00",
        active_end="22:00",
        popup_position="bottom_right",
        auto_close_seconds=12,
        autostart=True,
        sets=[Set(id="a", image_path="x", message="hi")],
    )
    base.update(overrides)
    return Config(**base)


def at(h, m=0):
    return datetime(2026, 4, 22, h, m)


# should_fire ----------

def test_skip_when_paused():
    c = make_config()
    s = State(date="2026-04-22", count=0, last_notified_at=None)
    assert scheduler.should_fire(now=at(10), cfg=c, state=s, paused=True) is False


def test_skip_outside_active_window():
    c = make_config()
    s = State(date="2026-04-22", count=0, last_notified_at=None)
    # 08:59 < 09:00
    assert scheduler.should_fire(now=at(8, 59), cfg=c, state=s, paused=False) is False
    # 22:00 — 종료 시각 포함 여부는 정책: "< end"로 판정 (22:00은 밖)
    assert scheduler.should_fire(now=at(22, 0), cfg=c, state=s, paused=False) is False


def test_fire_at_active_start_with_no_previous():
    c = make_config()
    s = State(date="2026-04-22", count=0, last_notified_at=None)
    assert scheduler.should_fire(now=at(9, 0), cfg=c, state=s, paused=False) is True


def test_skip_when_interval_not_elapsed():
    c = make_config(interval_minutes=60)
    s = State(date="2026-04-22", count=0, last_notified_at=at(10))
    # 10:59 → 59분 경과 < 60분
    assert scheduler.should_fire(now=at(10, 59), cfg=c, state=s, paused=False) is False


def test_fire_when_interval_elapsed():
    c = make_config(interval_minutes=60)
    s = State(date="2026-04-22", count=0, last_notified_at=at(10))
    # 11:00 → 60분 경과 >= 60
    assert scheduler.should_fire(now=at(11, 0), cfg=c, state=s, paused=False) is True


def test_skip_when_sets_empty():
    c = make_config(sets=[])
    s = State(date="2026-04-22", count=0, last_notified_at=None)
    assert scheduler.should_fire(now=at(10), cfg=c, state=s, paused=False) is False


# select_set ----------

def test_select_single_set_repeats():
    sets = [Set(id="a", image_path="x", message="m")]
    chosen = scheduler.select_set(sets=sets, last_id="a")
    assert chosen.id == "a"


def test_select_avoids_consecutive_duplicate():
    sets = [Set(id="a", image_path="x", message="m1"),
            Set(id="b", image_path="y", message="m2")]
    # last가 "a" → b만 가능
    for _ in range(20):
        assert scheduler.select_set(sets=sets, last_id="a").id == "b"


def test_select_returns_none_when_empty():
    assert scheduler.select_set(sets=[], last_id=None) is None


def test_select_random_when_no_last():
    sets = [Set(id="a", image_path="x", message="m1"),
            Set(id="b", image_path="y", message="m2"),
            Set(id="c", image_path="z", message="m3")]
    seen = set()
    for _ in range(50):
        seen.add(scheduler.select_set(sets=sets, last_id=None).id)
    assert seen == {"a", "b", "c"}
```

- [ ] **Step 2: 테스트 실패 확인**

```
pytest tests/test_scheduler.py -v
```
기대: 전부 FAIL — 모듈 없음.

- [ ] **Step 3: `src/scheduler.py` 구현**

파일: `C:\Users\PC-55\water_timer\src\scheduler.py`
```python
"""알림 발사 판정 + 세트 선택. 외부 부작용 없음 (Qt 의존 없음)."""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Optional, Sequence

from src.config import Config, Set, _parse_hhmm
from src.state import State


def _in_active_window(now: datetime, start: str, end: str) -> bool:
    """now의 시:분이 [start, end) 구간에 있으면 True."""
    mins = now.hour * 60 + now.minute
    return _parse_hhmm(start) <= mins < _parse_hhmm(end)


def should_fire(*, now: datetime, cfg: Config, state: State, paused: bool) -> bool:
    if paused:
        return False
    if not cfg.sets:
        return False
    if not _in_active_window(now, cfg.active_start, cfg.active_end):
        return False
    if state.last_notified_at is None:
        return True
    elapsed = now - state.last_notified_at
    return elapsed >= timedelta(minutes=cfg.interval_minutes)


def select_set(*, sets: Sequence[Set], last_id: Optional[str]) -> Optional[Set]:
    if not sets:
        return None
    if len(sets) == 1:
        return sets[0]
    candidates = [s for s in sets if s.id != last_id] or list(sets)
    return random.choice(candidates)
```

- [ ] **Step 4: 테스트 통과 확인**

```
pytest tests/test_scheduler.py -v
```
기대: 전부 PASS.

- [ ] **Step 5: 커밋**

```
git add src/scheduler.py tests/test_scheduler.py
git commit -m "feat(scheduler): add pure decision logic for fire and set selection"
```

---

## Task 6: 기본 이미지 placeholder 5장 생성

**Files:**
- Create: `src/assets/bundled/img1.png` ~ `img5.png`
- Create: `src/assets/icon.ico`

사용자가 실제 이미지를 제공하기 전까지 쓸 임시 placeholder. 각 이미지는 단색 배경에 "물방울" 유니코드 문자를 그린 256x256 PNG.

- [ ] **Step 1: placeholder 생성 스크립트 작성**

파일: `C:\Users\PC-55\water_timer\scripts\generate_placeholders.py`
```python
"""임시 placeholder 이미지 5장 + 앱 아이콘 .ico 생성.

사용자가 진짜 이미지를 주면 같은 파일명으로 덮어쓰기만 하면 된다.
PySide6의 QPixmap/QPainter를 쓰면 이미지 라이브러리 추가 의존 없이 처리 가능.
"""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap, QIcon, QImage
from PySide6.QtWidgets import QApplication

BASE = Path(__file__).resolve().parents[1] / "src" / "assets"
BUNDLED = BASE / "bundled"

COLORS = ["#4FC3F7", "#81D4FA", "#4DD0E1", "#80DEEA", "#29B6F6"]


def draw_drop(path: Path, color_hex: str, label: str, size: int = 256):
    pm = QPixmap(size, size)
    pm.fill(QColor(color_hex))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QColor("white"))
    font = QFont()
    font.setPointSize(80)
    p.setFont(font)
    p.drawText(pm.rect(), Qt.AlignCenter, "💧")
    font2 = QFont()
    font2.setPointSize(22)
    p.setFont(font2)
    p.drawText(pm.rect().adjusted(0, 160, 0, 0), Qt.AlignHCenter | Qt.AlignTop, label)
    p.end()
    pm.save(str(path), "PNG")


def main():
    app = QApplication([])
    BUNDLED.mkdir(parents=True, exist_ok=True)
    for i, color in enumerate(COLORS, start=1):
        draw_drop(BUNDLED / f"img{i}.png", color, f"#{i}")
    # 아이콘: 64x64 PNG → QIcon → .ico 저장
    icon_pm = QPixmap(64, 64)
    icon_pm.fill(QColor("#4FC3F7"))
    p = QPainter(icon_pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QColor("white"))
    font = QFont()
    font.setPointSize(28)
    p.setFont(font)
    p.drawText(icon_pm.rect(), Qt.AlignCenter, "💧")
    p.end()
    icon_pm.save(str(BASE / "icon.ico"), "ICO")
    print("생성 완료:", BUNDLED, BASE / "icon.ico")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 스크립트 실행**

Windows PowerShell:
```
.venv\Scripts\activate
python scripts\generate_placeholders.py
```
기대 결과: `src/assets/bundled/img1.png`~`img5.png`, `src/assets/icon.ico` 생성. 콘솔에 "생성 완료" 출력.

- [ ] **Step 3: 파일 존재 확인 (수동)**

`src/assets/bundled/` 폴더에 img1~img5.png, `src/assets/icon.ico`가 있는지 탐색기로 확인. 각 PNG를 열어보면 물방울과 번호가 그려져 있어야 함.

- [ ] **Step 4: 커밋**

```
git add scripts/generate_placeholders.py src/assets/
git commit -m "chore(assets): add placeholder images and icon generator"
```

---

## Task 7: `popup.py` — 알림 팝업 창

**Files:**
- Create: `src/popup.py`

UI라 pytest 대신 Task 8에서 전체 앱 통합 후 수동 검증.

- [ ] **Step 1: `src/popup.py` 작성**

파일: `C:\Users\PC-55\water_timer\src\popup.py`
```python
"""알림 팝업: 이미지 + 메시지 + '물 마셨음' 버튼.

- 프레임 없는 항상-위 창
- 340×220
- 사용자 설정 위치(corner)에 배치
- 자동 닫힘 N초 (카운터 증가 X)
- '물 마셨음' 클릭 시 즉시 닫힘 + on_drank() 콜백 호출
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QGuiApplication, QPixmap, QColor
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QGraphicsDropShadowEffect,
)


WIDTH = 340
HEIGHT = 220
MARGIN = 24           # 화면 가장자리와의 여백
THUMB = 128           # 이미지 썸네일 크기


def resolve_image_path(stored_path: str) -> Path:
    """<bundled>/xxx → 실제 경로로 치환."""
    if stored_path.startswith("<bundled>/"):
        if getattr(sys, "frozen", False):
            base = Path(sys._MEIPASS) / "assets" / "bundled"  # PyInstaller 런타임 경로
        else:
            base = Path(__file__).resolve().parent / "assets" / "bundled"
        return base / stored_path.replace("<bundled>/", "", 1)
    return Path(stored_path)


def fallback_icon_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets" / "icon.ico"
    return Path(__file__).resolve().parent / "assets" / "icon.ico"


class Popup(QWidget):
    def __init__(self,
                 image_path: str,
                 message: str,
                 auto_close_seconds: int,
                 position: str,
                 on_drank: Callable[[], None],
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._on_drank = on_drank
        self._closed = False

        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(WIDTH, HEIGHT)

        # --- 콘텐츠 컨테이너 (둥근 모서리 + 그림자) ---
        container = QWidget(self)
        container.setObjectName("container")
        container.setStyleSheet("""
            #container {
                background-color: white;
                border-radius: 16px;
            }
            QLabel#msg {
                font-family: 'Malgun Gothic', sans-serif;
                font-size: 14pt;
                color: #222;
            }
            QPushButton#drank {
                background-color: #4FC3F7;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 8px 14px;
                font-family: 'Malgun Gothic', sans-serif;
                font-size: 11pt;
            }
            QPushButton#drank:hover { background-color: #29B6F6; }
            QPushButton#close {
                background: transparent;
                color: #888;
                border: none;
                font-size: 14pt;
            }
            QPushButton#close:hover { color: #333; }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 60))
        container.setGraphicsEffect(shadow)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.addWidget(container)

        # --- 내부 레이아웃 ---
        h = QHBoxLayout(container)
        h.setContentsMargins(14, 14, 14, 14)
        h.setSpacing(14)

        img_label = QLabel()
        img_label.setFixedSize(THUMB, THUMB)
        img_label.setAlignment(Qt.AlignCenter)
        pm = QPixmap(str(resolve_image_path(image_path)))
        if pm.isNull():
            pm = QPixmap(str(fallback_icon_path()))
        img_label.setPixmap(
            pm.scaled(THUMB, THUMB, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        h.addWidget(img_label)

        right = QVBoxLayout()
        right.setSpacing(10)

        top_row = QHBoxLayout()
        msg_label = QLabel(message)
        msg_label.setObjectName("msg")
        msg_label.setWordWrap(True)
        msg_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        top_row.addWidget(msg_label, 1)

        close_btn = QPushButton("×")
        close_btn.setObjectName("close")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self._close_silently)
        top_row.addWidget(close_btn, 0, Qt.AlignTop)

        right.addLayout(top_row, 1)

        drank_btn = QPushButton("물 마셨음")
        drank_btn.setObjectName("drank")
        drank_btn.clicked.connect(self._mark_drank)
        right.addWidget(drank_btn, 0, Qt.AlignRight)

        h.addLayout(right, 1)

        # 위치 배치
        self._place(position)

        # 자동 닫힘 + 페이드 아웃
        self._auto_close_ms = max(3, auto_close_seconds) * 1000
        QTimer.singleShot(self._auto_close_ms - 400, self._fade_out)
        QTimer.singleShot(self._auto_close_ms, self._close_silently)

    def _place(self, position: str) -> None:
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x, y = {
            "top_left":     (screen.x() + MARGIN, screen.y() + MARGIN),
            "top_right":    (screen.right() - WIDTH - MARGIN, screen.y() + MARGIN),
            "bottom_left":  (screen.x() + MARGIN, screen.bottom() - HEIGHT - MARGIN),
            "bottom_right": (screen.right() - WIDTH - MARGIN, screen.bottom() - HEIGHT - MARGIN),
            "center":       (screen.x() + (screen.width() - WIDTH) // 2,
                             screen.y() + (screen.height() - HEIGHT) // 2),
        }.get(position, (screen.right() - WIDTH - MARGIN, screen.bottom() - HEIGHT - MARGIN))
        self.move(x, y)

    def _mark_drank(self):
        if self._closed:
            return
        self._closed = True
        try:
            self._on_drank()
        finally:
            self.close()

    def _close_silently(self):
        if self._closed:
            return
        self._closed = True
        self.close()

    def _fade_out(self):
        if self._closed:
            return
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(400)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._anim.start()
```

- [ ] **Step 2: 팝업 단독 실행 확인용 스모크 스크립트**

파일: `C:\Users\PC-55\water_timer\scripts\smoke_popup.py`
```python
"""팝업 단독 확인. `python scripts/smoke_popup.py` 로 실행."""
import sys
from PySide6.QtWidgets import QApplication

from src.popup import Popup


def main():
    app = QApplication(sys.argv)
    called = {"n": 0}
    def on_drank():
        called["n"] += 1
        print("drank!")
    p = Popup(
        image_path="<bundled>/img1.png",
        message="물 한 잔 어때요? 💧",
        auto_close_seconds=8,
        position="bottom_right",
        on_drank=on_drank,
    )
    p.show()
    app.exec()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 팝업 수동 확인**

Windows PowerShell:
```
.venv\Scripts\activate
python scripts\smoke_popup.py
```
확인 항목:
- 오른쪽 아래 구석에 흰 배경 둥근 모서리 팝업이 뜨는지
- 왼쪽에 파란 물방울 이미지가 보이는지
- 오른쪽에 메시지와 파란 "물 마셨음" 버튼이 있는지
- × 버튼을 누르면 즉시 닫히는지
- "물 마셨음"을 누르면 콘솔에 "drank!"가 찍히고 닫히는지
- 아무것도 안 눌러도 8초 후 자동 페이드 아웃되는지

- [ ] **Step 4: 커밋**

```
git add src/popup.py scripts/smoke_popup.py
git commit -m "feat(popup): add notification popup with image, message, auto-close"
```

---

## Task 8: `tray.py` + `app.py` — MVP 통합

**Files:**
- Create: `src/tray.py`
- Create: `src/app.py`

이 Task가 끝나면 사용자가 `python -m src.app`으로 실행해서 전체 흐름을 확인할 수 있다.

- [ ] **Step 1: `src/tray.py` 작성**

파일: `C:\Users\PC-55\water_timer\src\tray.py`
```python
"""시스템 트레이 아이콘 + 우클릭 메뉴."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu


class Tray(QSystemTrayIcon):
    def __init__(self,
                 icon_path: Path,
                 on_test_notify: Callable[[], None],
                 on_toggle_pause: Callable[[], None],
                 on_open_settings: Callable[[], None],
                 on_quit: Callable[[], None],
                 parent=None):
        super().__init__(QIcon(str(icon_path)), parent)
        self._on_test_notify = on_test_notify
        self._on_toggle_pause = on_toggle_pause
        self._on_open_settings = on_open_settings
        self._on_quit = on_quit

        self._menu = QMenu()
        self._count_action = self._menu.addAction("오늘 0번 마심")
        self._count_action.setEnabled(False)
        self._menu.addSeparator()

        self._test_action = self._menu.addAction("지금 바로 알림 보기")
        self._test_action.triggered.connect(self._on_test_notify)

        self._pause_action = self._menu.addAction("일시정지")
        self._pause_action.triggered.connect(self._on_toggle_pause)

        self._settings_action = self._menu.addAction("설정 열기")
        self._settings_action.triggered.connect(self._on_open_settings)

        self._menu.addSeparator()
        self._quit_action = self._menu.addAction("종료")
        self._quit_action.triggered.connect(self._on_quit)

        self.setContextMenu(self._menu)
        self.setToolTip("Water Timer")
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._on_open_settings()

    def set_count(self, count: int) -> None:
        self._count_action.setText(f"오늘 {count}번 마심")

    def set_paused(self, paused: bool) -> None:
        self._pause_action.setText("재개" if paused else "일시정지")

    def set_warning(self, text: str | None) -> None:
        self.setToolTip(text or "Water Timer")
```

- [ ] **Step 2: `src/app.py` 작성 (MVP 버전 — 설정창·자동시작·단일인스턴스는 이후 Task에서 추가)**

파일: `C:\Users\PC-55\water_timer\src\app.py`
```python
"""Water Timer 진입점 (MVP).

이 버전에서는 다음이 동작:
- 트레이 아이콘 상주
- 1분마다 scheduler tick → 조건 맞으면 팝업
- '지금 바로 알림 보기'로 수동 테스트
- 일시정지/재개
- 종료

아직 없음(후속 Task에서 추가): 설정 창, 자동 시작 레지스트리, 중복 실행 방지, 에러 로깅.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from src import config as config_mod
from src import scheduler
from src import state as state_mod
from src.popup import Popup, fallback_icon_path
from src.tray import Tray

TICK_MS = 60_000  # 1분


class Application:
    def __init__(self):
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setQuitOnLastWindowClosed(False)

        self.cfg = config_mod.load()
        self.state = state_mod.load()
        self.paused = False
        self.last_set_id: Optional[str] = None
        self.active_popup: Optional[Popup] = None

        self.tray = Tray(
            icon_path=fallback_icon_path(),
            on_test_notify=self.force_notify,
            on_toggle_pause=self.toggle_pause,
            on_open_settings=self.open_settings,
            on_quit=self.quit,
        )
        self.tray.show()
        self.tray.set_count(self.state.count)
        if not self.cfg.sets:
            self.tray.set_warning("등록된 이미지·메시지 세트가 없습니다. 설정에서 추가하세요.")

        self.timer = QTimer(self.qt_app)
        self.timer.timeout.connect(self.tick)
        self.timer.start(TICK_MS)

        # 시작 직후 한 번 판정 (09:00 진입 등 케이스)
        QTimer.singleShot(1000, self.tick)

    # ---------- 콜백 ----------

    def tick(self):
        # 날짜 전환 감지
        reloaded = state_mod.load()
        if reloaded.date != self.state.date:
            self.state = reloaded
            self.tray.set_count(self.state.count)

        now = datetime.now()
        if not scheduler.should_fire(now=now, cfg=self.cfg, state=self.state, paused=self.paused):
            return
        if self.active_popup is not None and self.active_popup.isVisible():
            return  # 이전 팝업 아직 떠 있음
        self.show_popup(now)

    def force_notify(self):
        if self.active_popup is not None and self.active_popup.isVisible():
            return
        if not self.cfg.sets:
            self.tray.showMessage("Water Timer", "등록된 세트가 없어요", icon=self.tray.Information)
            return
        self.show_popup(datetime.now(), force=True)

    def show_popup(self, now: datetime, force: bool = False):
        chosen = scheduler.select_set(sets=self.cfg.sets, last_id=self.last_set_id)
        if chosen is None:
            return
        self.last_set_id = chosen.id
        self.active_popup = Popup(
            image_path=chosen.image_path,
            message=chosen.message,
            auto_close_seconds=self.cfg.auto_close_seconds,
            position=self.cfg.popup_position,
            on_drank=self.on_drank,
        )
        self.active_popup.show()
        if not force:
            self.state = state_mod.update_last_notified(self.state, now)

    def on_drank(self):
        self.state = state_mod.increment_count(self.state)
        self.tray.set_count(self.state.count)

    def toggle_pause(self):
        self.paused = not self.paused
        self.tray.set_paused(self.paused)

    def open_settings(self):
        # MVP에서는 stub. Phase 2에서 구현.
        self.tray.showMessage("Water Timer", "설정 창은 곧 추가됩니다", icon=self.tray.Information)

    def quit(self):
        self.qt_app.quit()

    def run(self) -> int:
        return self.qt_app.exec()


def main():
    sys.exit(Application().run())


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 전체 테스트 suite 실행 (회귀 없는지 확인)**

```
pytest tests/ -v
```
기대: 모든 기존 테스트 PASS.

- [ ] **Step 4: MVP 수동 실행 및 체크리스트**

```
.venv\Scripts\activate
python -m src.app
```

수동 확인 체크리스트:
- [ ] 작업 표시줄 트레이에 물방울 아이콘이 뜬다
- [ ] 아이콘 우클릭하면 메뉴 5개(오늘 0번 마심 / 지금 바로 알림 보기 / 일시정지 / 설정 열기 / 종료)가 보인다
- [ ] "지금 바로 알림 보기" 클릭 → 오른쪽 아래에 팝업이 뜬다
- [ ] 팝업의 "물 마셨음" 클릭 → 팝업 닫히고 메뉴의 카운터가 "오늘 1번 마심"으로 바뀐다
- [ ] 팝업의 × 또는 자동 닫힘 → 카운터는 안 바뀐다
- [ ] 메뉴의 "일시정지" 클릭 → "재개"로 바뀐다. 다시 누르면 "일시정지"로
- [ ] "지금 바로 알림 보기"를 연타해도 동시에 두 개가 뜨지 않는다 (이전 팝업이 닫힌 뒤에만 새 팝업)
- [ ] "종료" 클릭 → 트레이 아이콘이 사라지고 프로세스 종료

- [ ] **Step 5: 커밋**

```
git add src/tray.py src/app.py
git commit -m "feat(app): integrate tray + scheduler + popup into MVP"
```

**🎯 Phase 1 완료 — 사용자에게 시연 가능한 최소 버전 동작.**

---

# Phase 2 — 설정 창

Phase 2 끝이면 사용자가 GUI로 간격, 활성시간, 위치, 이미지·메시지 세트, 자동 실행을 전부 바꿀 수 있다.

## Task 9: `settings_window.py` 골격 + 알림 탭

**Files:**
- Create: `src/settings_window.py`

- [ ] **Step 1: `src/settings_window.py` (탭 1개만 먼저)**

파일: `C:\Users\PC-55\water_timer\src\settings_window.py`
```python
"""설정 창 QDialog — 4개 탭.

탭 추가는 같은 파일 안에 _build_*_tab() 메서드로. 탭이 많아지면 분리를 고려.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QSpinBox, QTimeEdit, QComboBox, QDialogButtonBox, QMessageBox,
)

from src import config as config_mod


POSITION_LABELS = {
    "bottom_right": "오른쪽 아래",
    "bottom_left":  "왼쪽 아래",
    "top_right":    "오른쪽 위",
    "top_left":     "왼쪽 위",
    "center":       "중앙",
}


class SettingsWindow(QDialog):
    def __init__(self, cfg: config_mod.Config, on_save: Callable[[config_mod.Config], None],
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("Water Timer 설정")
        self.resize(520, 420)
        self._cfg = cfg
        self._on_save = on_save

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tabs.addTab(self._build_notify_tab(), "알림")
        # 탭 2~4는 Task 10~12에서 추가
        self.tabs.addTab(QWidget(), "이미지 & 메시지")
        self.tabs.addTab(QWidget(), "기록")
        self.tabs.addTab(QWidget(), "일반")

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    # ---------- 탭: 알림 ----------

    def _build_notify_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(config_mod.MIN_INTERVAL, config_mod.MAX_INTERVAL)
        self.interval_spin.setSuffix(" 분")
        self.interval_spin.setValue(self._cfg.interval_minutes)
        form.addRow("알림 간격", self.interval_spin)

        self.start_edit = QTimeEdit(QTime.fromString(self._cfg.active_start, "HH:mm"))
        self.start_edit.setDisplayFormat("HH:mm")
        form.addRow("활성 시간 시작", self.start_edit)

        self.end_edit = QTimeEdit(QTime.fromString(self._cfg.active_end, "HH:mm"))
        self.end_edit.setDisplayFormat("HH:mm")
        form.addRow("활성 시간 종료", self.end_edit)

        self.pos_combo = QComboBox()
        for key, label in POSITION_LABELS.items():
            self.pos_combo.addItem(label, key)
        self.pos_combo.setCurrentIndex(
            list(POSITION_LABELS.keys()).index(self._cfg.popup_position)
        )
        form.addRow("팝업 위치", self.pos_combo)

        self.close_spin = QSpinBox()
        self.close_spin.setRange(config_mod.MIN_AUTO_CLOSE, config_mod.MAX_AUTO_CLOSE)
        self.close_spin.setSuffix(" 초")
        self.close_spin.setValue(self._cfg.auto_close_seconds)
        form.addRow("자동 닫힘", self.close_spin)

        return w

    # ---------- 저장 ----------

    def _collect_notify_changes(self) -> dict:
        return dict(
            interval_minutes=self.interval_spin.value(),
            active_start=self.start_edit.time().toString("HH:mm"),
            active_end=self.end_edit.time().toString("HH:mm"),
            popup_position=self.pos_combo.currentData(),
            auto_close_seconds=self.close_spin.value(),
        )

    def _save(self):
        try:
            new_cfg = config_mod.replace(self._cfg, **self._collect_notify_changes())
            config_mod.save(new_cfg)
        except ValueError as e:
            QMessageBox.warning(self, "설정 오류", str(e))
            return
        self._cfg = new_cfg
        self._on_save(new_cfg)
        self.accept()
```

- [ ] **Step 2: `app.py`의 `open_settings` stub를 실제 창 호출로 교체**

파일: `C:\Users\PC-55\water_timer\src\app.py` 의 `open_settings` 메서드를 아래로 교체:

```python
    def open_settings(self):
        from src.settings_window import SettingsWindow
        dlg = SettingsWindow(self.cfg, on_save=self._on_config_saved)
        dlg.exec()

    def _on_config_saved(self, new_cfg):
        self.cfg = new_cfg
        if not self.cfg.sets:
            self.tray.set_warning("등록된 이미지·메시지 세트가 없습니다. 설정에서 추가하세요.")
        else:
            self.tray.set_warning(None)
```

- [ ] **Step 3: 수동 확인**

```
python -m src.app
```
- 트레이 "설정 열기" 클릭 → 설정 창이 뜬다
- 알림 탭에서 간격을 5분으로, 활성 시작을 지금 시각으로, 위치를 중앙으로 변경
- 저장 클릭 → 닫힘
- "지금 바로 알림 보기" → 팝업이 중앙에 뜬다
- 설정 다시 열면 변경한 값이 반영되어 있다
- 간격을 0으로 바꾸면 저장 시 에러 메시지 ("간격은 1~1440분..."). 저장 안 됨.

- [ ] **Step 4: 커밋**

```
git add src/settings_window.py src/app.py
git commit -m "feat(settings): add settings window skeleton with notification tab"
```

---

## Task 10: 설정 창 — 이미지 & 메시지 탭

**Files:**
- Modify: `src/settings_window.py` (두 번째 탭 구현)

QListWidget에 세트 목록, 오른쪽에 이미지 경로(QLineEdit + 파일 선택 버튼) + 메시지(QLineEdit) + 추가·삭제 버튼.

- [ ] **Step 1: 두 번째 탭 구현 추가**

파일: `src/settings_window.py` 수정:
1) `__init__`에서 `self.tabs.addTab(QWidget(), "이미지 & 메시지")` 줄을 `self.tabs.addTab(self._build_sets_tab(), "이미지 & 메시지")`로 교체.
2) 기존 import 블록 확장:
```python
from PySide6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QSpinBox, QTimeEdit, QComboBox, QDialogButtonBox, QMessageBox,
    QListWidget, QListWidgetItem, QLineEdit, QPushButton, QLabel,
    QFileDialog, QSplitter,
)
```
3) 클래스 내부에 아래 메서드 추가:
```python
    def _build_sets_tab(self) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)

        # 좌측: 목록 + 추가/삭제
        left = QVBoxLayout()
        self.sets_list = QListWidget()
        self._reload_sets_list()
        self.sets_list.currentRowChanged.connect(self._on_set_selected)
        left.addWidget(self.sets_list)
        btn_row = QHBoxLayout()
        add_btn = QPushButton("추가")
        add_btn.clicked.connect(self._add_set)
        rm_btn = QPushButton("삭제")
        rm_btn.clicked.connect(self._remove_set)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(rm_btn)
        left.addLayout(btn_row)
        h.addLayout(left, 1)

        # 우측: 편집 폼
        right = QVBoxLayout()
        form = QFormLayout()
        self.img_edit = QLineEdit()
        self.img_edit.setPlaceholderText("이미지 파일 경로")
        browse = QPushButton("찾아보기…")
        browse.clicked.connect(self._browse_image)
        img_row = QHBoxLayout()
        img_row.addWidget(self.img_edit, 1)
        img_row.addWidget(browse)
        form.addRow("이미지", self._wrap(img_row))
        self.msg_edit = QLineEdit()
        self.msg_edit.setPlaceholderText("표시할 메시지")
        form.addRow("메시지", self.msg_edit)
        self.img_status = QLabel("")
        self.img_status.setStyleSheet("color: #c62828;")
        form.addRow("", self.img_status)
        right.addLayout(form)
        apply_btn = QPushButton("이 세트 수정 적용")
        apply_btn.clicked.connect(self._apply_set_edit)
        right.addWidget(apply_btn, 0)
        right.addStretch(1)
        h.addLayout(right, 2)

        return w

    def _wrap(self, layout) -> QWidget:
        wrapper = QWidget()
        wrapper.setLayout(layout)
        return wrapper

    def _reload_sets_list(self):
        self.sets_list.clear()
        for s in self._cfg.sets:
            self.sets_list.addItem(QListWidgetItem(f"{s.id} — {s.message[:30]}"))

    def _on_set_selected(self, row: int):
        if row < 0 or row >= len(self._cfg.sets):
            self.img_edit.setText("")
            self.msg_edit.setText("")
            self.img_status.setText("")
            return
        s = self._cfg.sets[row]
        self.img_edit.setText(s.image_path)
        self.msg_edit.setText(s.message)
        self._update_img_status(s.image_path)

    def _update_img_status(self, path_str: str):
        from src.popup import resolve_image_path
        from pathlib import Path as _P
        p = resolve_image_path(path_str) if path_str else _P("")
        if not path_str:
            self.img_status.setText("")
        elif path_str.startswith("<bundled>/") or p.exists():
            self.img_status.setText("")
        else:
            self.img_status.setText(f"경고: 이미지 파일을 찾을 수 없습니다 ({path_str})")

    def _browse_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "이미지 선택", "",
            "이미지 (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
        )
        if path:
            self.img_edit.setText(path)
            self._update_img_status(path)

    def _add_set(self):
        new = config_mod.Set(id=config_mod.new_set_id(),
                             image_path="", message="새 메시지")
        self._cfg = config_mod.add_set(self._cfg, new)
        self._reload_sets_list()
        self.sets_list.setCurrentRow(len(self._cfg.sets) - 1)

    def _remove_set(self):
        row = self.sets_list.currentRow()
        if row < 0 or row >= len(self._cfg.sets):
            return
        s = self._cfg.sets[row]
        self._cfg = config_mod.remove_set(self._cfg, s.id)
        self._reload_sets_list()

    def _apply_set_edit(self):
        row = self.sets_list.currentRow()
        if row < 0 or row >= len(self._cfg.sets):
            return
        s = self._cfg.sets[row]
        self._cfg = config_mod.update_set(
            self._cfg, s.id,
            image_path=self.img_edit.text().strip(),
            message=self.msg_edit.text().strip(),
        )
        self._reload_sets_list()
        self.sets_list.setCurrentRow(row)
```

- [ ] **Step 2: 수동 확인**

```
python -m src.app
```
- 설정 → "이미지 & 메시지" 탭
- 좌측에 기본 5세트 목록
- 하나 선택 → 우측에 이미지 경로와 메시지 표시
- "찾아보기…"로 이미지 파일 선택 → 경로가 채워짐
- 메시지 수정 → "이 세트 수정 적용" → 좌측 목록의 preview 텍스트 변경
- "추가" → 새 세트 생성, "삭제" → 제거
- 유효하지 않은 이미지 경로 입력 → 경고 라벨 빨갛게
- 저장 후 창 닫고 "지금 바로 알림 보기" → 반영됨

- [ ] **Step 3: 커밋**

```
git add src/settings_window.py
git commit -m "feat(settings): implement image & message sets tab"
```

---

## Task 11: 설정 창 — 기록 탭

**Files:**
- Modify: `src/settings_window.py`

오늘 마신 횟수 표시 + 수동 초기화 버튼.

- [ ] **Step 1: `__init__`의 세 번째 탭 교체**

`self.tabs.addTab(QWidget(), "기록")` → `self.tabs.addTab(self._build_history_tab(), "기록")`.
`__init__` 인자에 `current_count: int`를 추가 (기본값 0). 아래 클래스 시그니처도 바꿈:

```python
class SettingsWindow(QDialog):
    def __init__(self, cfg: config_mod.Config,
                 current_count: int,
                 on_save: Callable[[config_mod.Config], None],
                 on_reset_count: Callable[[], None],
                 parent=None):
        ...
        self._current_count = current_count
        self._on_reset_count = on_reset_count
```

- [ ] **Step 2: 기록 탭 메서드 추가**

```python
    def _build_history_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        self.count_label = QLabel(f"오늘 {self._current_count}번 마셨어요")
        self.count_label.setStyleSheet("font-size: 16pt; padding: 20px;")
        v.addWidget(self.count_label)
        reset_btn = QPushButton("오늘 횟수 초기화")
        reset_btn.clicked.connect(self._reset_count)
        v.addWidget(reset_btn, 0)
        v.addStretch(1)
        return w

    def _reset_count(self):
        if QMessageBox.question(self, "확인",
                                "오늘 카운터를 0으로 초기화할까요?") != QMessageBox.Yes:
            return
        self._on_reset_count()
        self.count_label.setText("오늘 0번 마셨어요")
```

- [ ] **Step 3: `app.py`의 호출 지점 업데이트**

`open_settings` 메서드를 아래로 교체:

```python
    def open_settings(self):
        from src.settings_window import SettingsWindow
        dlg = SettingsWindow(
            cfg=self.cfg,
            current_count=self.state.count,
            on_save=self._on_config_saved,
            on_reset_count=self._reset_count,
        )
        dlg.exec()

    def _reset_count(self):
        from dataclasses import replace
        self.state = replace(self.state, count=0)
        from src import state as state_mod
        state_mod.save(self.state)
        self.tray.set_count(0)
```

- [ ] **Step 4: 수동 확인**

- 설정 → 기록 탭 → "오늘 N번 마셨어요" 표시
- "오늘 횟수 초기화" 확인창 → Yes → 0으로 바뀜
- 트레이 메뉴의 카운터도 0으로 바뀜
- 팝업 → "물 마셨음" → 1 증가 확인

- [ ] **Step 5: 커밋**

```
git add src/settings_window.py src/app.py
git commit -m "feat(settings): add history tab with count reset"
```

---

## Task 12: 설정 창 — 일반 탭 (자동 시작 토글은 Task 13 이후 연결)

**Files:**
- Modify: `src/settings_window.py`

자동 시작 토글 + 버전 정보. 토글 동작 자체는 Task 13에서 `autostart.py` 만든 뒤에 연결.

- [ ] **Step 1: 네 번째 탭 구현**

`__init__`에서 `self.tabs.addTab(QWidget(), "일반")` → `self.tabs.addTab(self._build_general_tab(), "일반")`.

`src/__init__.py`에 버전 상수 추가:
```python
# src/__init__.py
__version__ = "0.1.0"
```

import 추가:
```python
from PySide6.QtWidgets import (
    ..., QCheckBox,
)
```

메서드 추가:
```python
    def _build_general_tab(self) -> QWidget:
        from src import __version__
        w = QWidget()
        v = QVBoxLayout(w)
        self.autostart_check = QCheckBox("Windows 시작 시 자동 실행")
        self.autostart_check.setChecked(self._cfg.autostart)
        v.addWidget(self.autostart_check)
        version_label = QLabel(f"Water Timer v{__version__}")
        version_label.setStyleSheet("color: #777; margin-top: 20px;")
        v.addWidget(version_label)
        v.addStretch(1)
        return w
```

`_collect_notify_changes`를 `_collect_changes`로 이름 변경하고 autostart 포함:
```python
    def _collect_changes(self) -> dict:
        return dict(
            interval_minutes=self.interval_spin.value(),
            active_start=self.start_edit.time().toString("HH:mm"),
            active_end=self.end_edit.time().toString("HH:mm"),
            popup_position=self.pos_combo.currentData(),
            auto_close_seconds=self.close_spin.value(),
            autostart=self.autostart_check.isChecked(),
        )
```

`_save`도 `_collect_notify_changes`를 `_collect_changes`로 바꿈.

- [ ] **Step 2: 수동 확인**

- 설정 → 일반 탭 → 체크박스·버전 표시
- 토글 상태가 저장되어서 설정 다시 열면 유지됨 (실제 Windows 자동 등록은 Task 13 이후)

- [ ] **Step 3: 커밋**

```
git add src/settings_window.py src/__init__.py
git commit -m "feat(settings): add general tab with autostart toggle and version"
```

**🎯 Phase 2 완료 — 사용자가 GUI로 모든 설정을 바꿀 수 있음.**

---

# Phase 3 — 시스템 통합

## Task 13: `autostart.py` — Windows 레지스트리 Run 키

**Files:**
- Create: `src/autostart.py`
- Create: `tests/test_autostart.py`

winreg는 Windows 전용 표준 라이브러리. 비Windows 환경(CI 등)에서는 테스트가 스킵되도록 가드.

- [ ] **Step 1: 테스트 작성**

파일: `C:\Users\PC-55\water_timer\tests\test_autostart.py`
```python
import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows 전용")

from src import autostart


def test_enable_disable_roundtrip(tmp_path):
    fake_exe = tmp_path / "WaterTimer.exe"
    fake_exe.write_bytes(b"")
    autostart.set_autostart(True, str(fake_exe))
    assert autostart.get_autostart() is True
    assert autostart.get_registered_path() == str(fake_exe)

    autostart.set_autostart(False, str(fake_exe))
    assert autostart.get_autostart() is False


def test_disable_when_not_registered_is_noop(tmp_path):
    fake_exe = tmp_path / "WaterTimer.exe"
    fake_exe.write_bytes(b"")
    # 상태 무관하게 호출 가능해야 함
    autostart.set_autostart(False, str(fake_exe))
    assert autostart.get_autostart() is False
```

- [ ] **Step 2: 테스트 실패 확인**

```
pytest tests/test_autostart.py -v
```
기대: 모듈 없음 에러.

- [ ] **Step 3: `src/autostart.py` 구현**

파일: `C:\Users\PC-55\water_timer\src\autostart.py`
```python
"""Windows 시작 시 자동 실행.

HKCU\Software\Microsoft\Windows\CurrentVersion\Run 에
앱 실행 경로를 값으로 저장한다.
"""
from __future__ import annotations

import sys

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "WaterTimer"


def _winreg():
    import winreg  # Windows 전용
    return winreg


def set_autostart(enabled: bool, exe_path: str) -> None:
    if sys.platform != "win32":
        return
    winreg = _winreg()
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                        winreg.KEY_SET_VALUE) as key:
        if enabled:
            # 경로에 공백이 있는 경우 대비 quote
            value = f'"{exe_path}"'
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, value)
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass  # 이미 없으면 OK


def get_autostart() -> bool:
    if sys.platform != "win32":
        return False
    winreg = _winreg()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
            return True
    except FileNotFoundError:
        return False


def get_registered_path() -> str | None:
    if sys.platform != "win32":
        return None
    winreg = _winreg()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
            # 저장은 quote 포함 → 반환 시 제거
            return value.strip('"')
    except FileNotFoundError:
        return None


def current_exe_path() -> str:
    """런타임에 자기 자신 경로 추출. PyInstaller 빌드 시 sys.executable 사용."""
    if getattr(sys, "frozen", False):
        return sys.executable
    import os
    # 개발 환경: python.exe -m src.app → sys.executable + 현재 스크립트
    return os.path.abspath(sys.argv[0]) or sys.executable
```

- [ ] **Step 4: 테스트 통과 확인**

```
pytest tests/test_autostart.py -v
```
기대: PASS (Windows에서). 다른 OS에선 skip.

- [ ] **Step 5: `app.py` 시작 시 동기화 + 설정 저장 시 동기화**

`src/app.py`의 `Application.__init__` 맨 아래에 추가:
```python
        # 자동 시작 레지스트리 동기화
        self._sync_autostart()
```

메서드 추가:
```python
    def _sync_autostart(self):
        from src import autostart
        exe = autostart.current_exe_path()
        autostart.set_autostart(self.cfg.autostart, exe)
```

그리고 `_on_config_saved` 끝에도 추가:
```python
    def _on_config_saved(self, new_cfg):
        self.cfg = new_cfg
        if not self.cfg.sets:
            self.tray.set_warning("등록된 이미지·메시지 세트가 없습니다. 설정에서 추가하세요.")
        else:
            self.tray.set_warning(None)
        self._sync_autostart()
```

- [ ] **Step 6: 수동 확인**

Windows PowerShell:
```
python -m src.app
```
- 트레이 → 설정 → 일반 → "Windows 시작 시 자동 실행" 체크 후 저장
- 레지스트리 에디터(`regedit`)에서 `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`에 `WaterTimer` 값 등록 확인
- 해제 후 저장 → 값 삭제 확인

- [ ] **Step 7: 커밋**

```
git add src/autostart.py tests/test_autostart.py src/app.py
git commit -m "feat(autostart): sync config.autostart with HKCU Run key"
```

---

## Task 14: `single_instance.py` — 중복 실행 방지

**Files:**
- Create: `src/single_instance.py`

Windows named mutex를 `ctypes`로 호출 (pywin32 의존 없음). 이미 실행 중이면 두 번째 인스턴스는 즉시 종료.

- [ ] **Step 1: `src/single_instance.py` 작성**

파일: `C:\Users\PC-55\water_timer\src\single_instance.py`
```python
"""Windows named mutex로 동시에 한 인스턴스만 실행되도록 보장.

한계: 기존 인스턴스에 "설정 창 열기"를 시그널링하는 것은 v1 스코프 밖.
두 번째 실행은 그냥 종료되고, 사용자가 트레이 아이콘을 클릭해야 함.
"""
from __future__ import annotations

import ctypes
import sys

MUTEX_NAME = "Global\\WaterTimer_SingleInstance_Mutex_v1"
ERROR_ALREADY_EXISTS = 183


class SingleInstanceGuard:
    """실행 중인 동안 named mutex를 잡고 있는 컨텍스트."""

    def __init__(self):
        self._handle = None

    def __enter__(self):
        if sys.platform != "win32":
            return self
        self._handle = ctypes.windll.kernel32.CreateMutexW(
            None, False, MUTEX_NAME
        )
        if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            raise AlreadyRunning()
        return self

    def __exit__(self, *args):
        if self._handle:
            ctypes.windll.kernel32.CloseHandle(self._handle)
            self._handle = None


class AlreadyRunning(RuntimeError):
    pass
```

- [ ] **Step 2: `app.py`의 `main()`에 가드 적용**

`src/app.py` 맨 아래의 `main`을 교체:

```python
def main():
    from src.single_instance import SingleInstanceGuard, AlreadyRunning
    try:
        with SingleInstanceGuard():
            sys.exit(Application().run())
    except AlreadyRunning:
        # 조용히 종료. Qt 메시지 박스를 띄우려면 QApplication이 필요해서
        # 간단히 Windows MessageBox를 직접 호출.
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0, "Water Timer가 이미 실행 중입니다.", "Water Timer", 0x40
            )
        sys.exit(0)
```

- [ ] **Step 3: 수동 확인**

```
python -m src.app
```
첫 번째 실행 중인 상태에서 새 PowerShell 창 열고 같은 명령 재실행 → 메시지 박스 "이미 실행 중" → 두 번째 프로세스 종료. 첫 번째는 계속 동작.

- [ ] **Step 4: 커밋**

```
git add src/single_instance.py src/app.py
git commit -m "feat(single-instance): prevent multiple instances via named mutex"
```

---

## Task 15: `error_log.py` — 에러 로깅 + 글로벌 예외 훅

**Files:**
- Create: `src/error_log.py`

- [ ] **Step 1: `src/error_log.py` 작성**

파일: `C:\Users\PC-55\water_timer\src\error_log.py`
```python
"""error.log 로깅 설정 + 글로벌 예외 훅.

사용자에게는 Qt 메시지박스로 간단히 알리고, 상세는 %APPDATA%\WaterTimer\error.log에 기록.
"""
from __future__ import annotations

import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler

from src import paths

_logger: logging.Logger | None = None


def setup() -> logging.Logger:
    global _logger
    if _logger:
        return _logger
    log = logging.getLogger("water_timer")
    log.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        paths.error_log_path(), maxBytes=512_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s"
    ))
    log.addHandler(handler)
    _logger = log
    return log


def install_excepthook():
    log = setup()

    def _hook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        log.error("Unhandled exception:\n%s",
                  "".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
        # 사용자에게 알림
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            if QApplication.instance():
                QMessageBox.critical(
                    None, "Water Timer 오류",
                    "예상치 못한 오류가 발생했습니다.\n자세한 내용은 error.log를 확인해 주세요."
                )
        except Exception:
            pass

    sys.excepthook = _hook
```

- [ ] **Step 2: `app.py`의 `main`에 첫 줄로 추가**

`src/app.py`의 `main` 함수 맨 앞에:
```python
def main():
    from src.error_log import install_excepthook
    install_excepthook()
    from src.single_instance import SingleInstanceGuard, AlreadyRunning
    ...
```

- [ ] **Step 3: 수동 확인 — 로그가 실제로 기록되는지**

PowerShell에서 일회성 에러를 발생시켜 로그 동작만 검증 (앱 코드는 건드리지 않음):
```
.venv\Scripts\activate
python -c "from src.error_log import install_excepthook; install_excepthook(); raise RuntimeError('테스트 에러')"
```

확인:
- 프로세스가 에러와 함께 종료된다.
- `%APPDATA%\WaterTimer\error.log` 파일이 생성되고, 그 안에 `Unhandled exception:` 문자열 아래에 `RuntimeError: 테스트 에러`가 기록되어 있다.
- 파일을 다시 열어도 (앱 재실행 후) 이전 기록이 남아 있다(RotatingFileHandler는 append 모드).

- [ ] **Step 4: 커밋**

```
git add src/error_log.py src/app.py
git commit -m "feat(logging): add rotating error.log and global exception hook"
```

**🎯 Phase 3 완료 — 자동 실행·중복 방지·에러 로깅 장착.**

---

# Phase 4 — 배포 (PyInstaller)

## Task 16: PyInstaller build.spec + 빌드 스크립트

**Files:**
- Create: `build.spec`
- Create: `build.bat`

- [ ] **Step 1: `build.spec` 작성**

파일: `C:\Users\PC-55\water_timer\build.spec`
```python
# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — 단일 .exe 생성.
# 빌드: pyinstaller build.spec  (또는 build.bat)

from pathlib import Path

ROOT = Path.cwd()

a = Analysis(
    [str(ROOT / "src" / "app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "src" / "assets" / "bundled"), "assets/bundled"),
        (str(ROOT / "src" / "assets" / "icon.ico"), "assets"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="WaterTimer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,              # --windowed
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "src" / "assets" / "icon.ico"),
)
```

- [ ] **Step 2: `build.bat` 작성**

파일: `C:\Users\PC-55\water_timer\build.bat`
```
@echo off
REM Water Timer 빌드 스크립트 (Windows)
call .venv\Scripts\activate
if exist dist rmdir /S /Q dist
if exist build rmdir /S /Q build
pyinstaller build.spec
echo.
echo 완료: dist\WaterTimer.exe
```

- [ ] **Step 3: 빌드 실행**

```
build.bat
```
기대 결과:
- `dist\WaterTimer.exe` 생성 (약 40~70MB)
- 에러 없이 종료

- [ ] **Step 4: 빌드 결과 수동 테스트**

탐색기에서 `dist\WaterTimer.exe`를 아무 곳(예: 바탕화면)에 복사 후 더블클릭.
체크리스트:
- [ ] 트레이 아이콘 뜸
- [ ] "지금 바로 알림 보기" → 팝업 정상 (이미지·메시지 모두 표시)
- [ ] 설정 창 열기/저장 OK
- [ ] 자동 시작 토글 → 레지스트리 반영
- [ ] `%APPDATA%\WaterTimer\config.json`, `today.json` 생성 확인
- [ ] `dist\WaterTimer.exe`를 두 번째로 실행하면 "이미 실행 중" 메시지

- [ ] **Step 5: 커밋**

```
git add build.spec build.bat
git commit -m "build: add PyInstaller spec and build batch script"
```

---

## Task 17: 최종 QA 체크리스트 + README

**Files:**
- Create: `README.md`

사용자(비전공자)가 앱을 받았을 때 볼 수 있는 간단한 설명 + 개발자(Claude 포함 미래 에이전트)가 유지보수할 때 볼 수 있는 실행 방법.

- [ ] **Step 1: `README.md` 작성**

파일: `C:\Users\PC-55\water_timer\README.md`
```markdown
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

### 개발 실행

```
python -m src.app
```

### 테스트

```
pytest tests/ -v
```

### 빌드

```
build.bat
```
결과물: `dist\WaterTimer.exe`

### 문서

- 설계: `docs/superpowers/specs/2026-04-22-water-timer-design.md`
- 구현 계획: `docs/superpowers/plans/2026-04-22-water-timer-implementation.md`
```

- [ ] **Step 2: 최종 회귀 테스트**

```
pytest tests/ -v
```
기대: 전부 PASS.

- [ ] **Step 3: 최종 수동 QA (전체 시나리오)**

체크리스트:
- [ ] 깨끗한 Windows 사용자 계정(또는 %APPDATA%\WaterTimer 삭제 후)에서 .exe 첫 실행 → 에러 없이 트레이 아이콘 등장
- [ ] 실행 후 **3초 이내** 트레이 아이콘이 보임 (비기능 요구사항 §5)
- [ ] 트레이 메뉴 5항목 전부 동작
- [ ] 설정 4탭 전부 동작 (알림 / 이미지&메시지 / 기록 / 일반)
- [ ] 간격을 1분으로 해두고 2분 대기 → 자동 팝업 1회 뜸 (몰아치지 않음)
- [ ] "물 마셨음" → 카운터 +1, 트레이 메뉴와 기록 탭 모두 반영
- [ ] 일시정지 중에는 자동 팝업 안 뜸
- [ ] 자동 시작 ON → 재부팅 후 자동 실행 (실제 재부팅 테스트 1회)
- [ ] 두 번째 실행 시 "이미 실행 중" 메시지
- [ ] 작업 관리자에서 `WaterTimer.exe` 메모리 사용량이 **100MB 이하** 유지 (비기능 요구사항 §5)

- [ ] **Step 4: 커밋**

```
git add README.md
git commit -m "docs: add README with user and developer guides"
```

**🎯 Phase 4 완료 — 배포 가능한 단일 .exe 완성.**

---

# 오픈 이슈 (구현 시 사용자에게 받아야 함)

1. **실제 기본 이미지 5장**: Task 6의 placeholder PNG를 사용자가 제공하는 실제 이미지로 대체한 뒤 재빌드. 파일명만 `img1.png`~`img5.png`로 맞추면 된다.
2. **앱 아이콘 `.ico`**: 16x16, 32x32, 48x48, 256x256 멀티사이즈 아이콘. 마찬가지로 받으면 `src/assets/icon.ico`를 교체.

둘 다 없어도 placeholder로 Phase 4까지 완주 가능. 교체는 파일만 덮어쓰고 재빌드하면 끝.

---

# v2로 미룬 것 (스펙 §14 참고)

섭취량(ml), 통계·그래프, 소리 알림, 다국어, macOS/Linux, 자동 업데이트, 자정 넘는 활성 시간대.
