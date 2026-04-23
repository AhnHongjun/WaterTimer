# Popup Fix + 캐릭터 멀티 선택 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 팝업 버튼 클릭 불가 버그 수정, "마셨어요!" 파티클 모양 정상화, 캐릭터(빌트인 3종 + 업로드 이미지) 개별 토글로 멀티 선택 가능하게 통합.

**Architecture:** 순수 데이터 스키마 변경(`character_id` 단일 → `active_character_ids` 리스트) + 팝업 창 플래그 1줄 교체 + 파티클 페인팅 수정 + 설정창 토글 UI. 기존 `popup.py` 캐릭터 패널 분기 로직은 그대로 두고 app.py에서 매 호출마다 "빌트인/커스텀" 중 하나를 뽑아 기존 API에 매핑.

**Tech Stack:** Python 3.12, PySide6 6.6.3, pytest, PyInstaller.

---

## 파일 구조 (변경 범위)

```
water_timer/
├── src/
│   ├── config.py            # character_id 제거 + active_character_ids 추가 + 마이그레이션
│   ├── popup.py             # Qt.Tool → Qt.Dialog, _DropParticle paintEvent 재작성
│   ├── app.py               # _pick_image → _pick_for_popup 확장
│   └── settings_window.py   # _CharacterCard 토글 + _CustomPanel rebuild 로직 + hint
└── tests/
    └── test_config.py       # character_id 참조 수정 + 마이그레이션 테스트 추가
```

**책임 분리:**
- `config.py`: 데이터 스키마·검증·마이그레이션 (순수 로직)
- `popup.py`: UI 프레젠테이션 + 창 설정
- `app.py`: 런타임 선택 로직 + 팝업 인자 매핑
- `settings_window.py`: 설정 탭 UI 조작 (_CustomPanel만)
- `tests/test_config.py`: 스키마 계약 검증

---

## Task 1: 팝업 창 플래그 교체 (Qt.Tool → Qt.Dialog)

**Files:**
- Modify: `src/popup.py:217`

작업자 메모: 이 변경만으로 트레이 기반 앱 컨텍스트에서 팝업이 입력 활성화를 받지 못하던 Qt/Windows 이슈가 해결된다. 부작용은 팝업이 뜬 12초 동안 작업표시줄에 항목이 잠깐 보인다는 것뿐.

- [ ] **Step 1: popup.py의 창 플래그 한 줄 수정**

파일 `C:\Users\PC-55\water_timer\src\popup.py` 의 `Popup.__init__` 안에서 찾을 줄:

```python
self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
```

로 바꿔서:

```python
self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
```

- [ ] **Step 2: import·구문 검증**

```
cd /c/Users/PC-55/water_timer
.venv/Scripts/python.exe -c "from src.popup import Popup; print('ok')"
```
기대 출력: `ok`

- [ ] **Step 3: 기존 테스트 회귀 확인**

```
.venv/Scripts/pytest.exe tests/ -q
```
기대: 77 passed.

- [ ] **Step 4: 커밋**

```
cd /c/Users/PC-55/water_timer
git add src/popup.py
git commit -m "fix(popup): use Qt.Dialog flag so tray-launched popup receives clicks

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: `_DropParticle` 경로 재작성

**Files:**
- Modify: `src/popup.py:72-84`

작업자 메모: 기존 경로는 SVG `M...C...A...C...Z` 를 직역하면서 `QRect(int(...))` 로 정수 절삭된 arc rect가 직전 cubic 종단점과 어긋나 작은 사이즈에서 찢어진 모양을 만들었다. 2개의 cubic 곡선만으로 깔끔한 물방울을 그리도록 교체.

- [ ] **Step 1: `_DropParticle.paintEvent` 전체 교체**

파일 `C:\Users\PC-55\water_timer\src\popup.py` 의 `_DropParticle` 클래스 `paintEvent` 메서드를 **전체** 아래로 교체:

```python
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx = w / 2
        path = QPainterPath()
        # 위 꼭짓점에서 시작해 우측 곡선으로 하단까지, 다시 좌측 곡선으로 위로 닫는 물방울
        path.moveTo(cx, 0)
        path.cubicTo(w, h * 0.45, w, h * 0.75, cx, h)
        path.cubicTo(0, h * 0.75, 0, h * 0.45, cx, 0)
        path.closeSubpath()
        p.fillPath(path, QBrush(self._color))
```

- [ ] **Step 2: `QRect` import 제거 확인**

파일 상단의 `from PySide6.QtCore import ...` 에 `QRect` 가 더 이상 쓰이지 않으면 제거해도 되지만(이 줄 외 다른 곳에서 QRect 사용 여부 확인), 다른 곳에서 쓰고 있으면 그대로 둔다. 먼저 확인:

```
cd /c/Users/PC-55/water_timer
grep -n "QRect\b" src/popup.py
```

`QRect`가 다른 줄에서 사용되고 있으면 import는 유지. 그렇지 않으면 해당 import 토큰만 지운다(예: `QRect, QRectF` → `QRectF`, `QRect,` 제거). 나머지 import 줄은 그대로.

- [ ] **Step 3: 모듈 로드 확인**

```
.venv/Scripts/python.exe -c "from src.popup import Popup, _DropParticle; print('ok')"
```

- [ ] **Step 4: 회귀 테스트**

```
.venv/Scripts/pytest.exe tests/ -q
```
기대: 77 passed.

- [ ] **Step 5: 커밋**

```
git add src/popup.py
git commit -m "fix(popup): redraw particle with two cubic beziers for clean teardrop

Prior SVG-direct translation used int-truncated QRect for the arc
subpath, which at small sizes (8-12px) mismatched the preceding cubic
endpoint and produced torn shapes. Two-cubic path is robust.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: `config.py` 스키마 변경 + 마이그레이션 + 검증 (TDD)

**Files:**
- Modify: `src/config.py`
- Modify: `tests/test_config.py`

작업자 메모: `character_id` 단일 값을 `active_character_ids: list[str]` (`{"happy","excited","sleepy"}`의 부분집합) 로 대체. 기존 저장된 `character_id` 값은 자동 변환. TDD로 마이그레이션·검증 먼저 검증 테스트 추가.

- [ ] **Step 1: 실패 테스트 추가**

파일 `C:\Users\PC-55\water_timer\tests\test_config.py` — 기존 `test_valid_character` / `test_invalid_character_rejected` 블록 **뒤에** 다음 테스트 추가:

```python
def test_default_active_character_ids_is_happy(config_file):
    c = config.load()
    assert c.active_character_ids == ["happy"]


def test_migrates_builtin_character_id_to_list(config_file):
    """기존 config에 character_id='sleepy' 만 있으면 active_character_ids=['sleepy']로 마이그레이션."""
    config_file.parent.mkdir(parents=True, exist_ok=True)
    v2_data = {
        "interval_minutes": 60,
        "active_start": "09:00",
        "active_end": "22:00",
        "popup_position": "bottom_right",
        "auto_close_seconds": 12,
        "autostart": True,
        "sets": [],
        "character_id": "sleepy",
    }
    config_file.write_text(json.dumps(v2_data, ensure_ascii=False), encoding="utf-8")
    c = config.load()
    assert c.active_character_ids == ["sleepy"]


def test_migrates_custom_character_id_to_empty_builtin_list(config_file):
    """character_id='custom' 이면 빌트인은 전부 비활성. (업로드 이미지 쪽에서 처리)"""
    config_file.parent.mkdir(parents=True, exist_ok=True)
    v2_data = {
        "interval_minutes": 60,
        "active_start": "09:00",
        "active_end": "22:00",
        "popup_position": "bottom_right",
        "auto_close_seconds": 12,
        "autostart": True,
        "sets": [],
        "character_id": "custom",
    }
    config_file.write_text(json.dumps(v2_data, ensure_ascii=False), encoding="utf-8")
    c = config.load()
    assert c.active_character_ids == []


@pytest.mark.parametrize("ids", [[], ["happy"], ["happy", "sleepy"],
                                 ["happy", "excited", "sleepy"]])
def test_validate_character_list_accepts_subsets(ids):
    config.validate_character_list(ids)  # no raise


@pytest.mark.parametrize("ids", [["grumpy"], ["happy", "unknown"],
                                 "not a list", [123]])
def test_validate_character_list_rejects_invalid(ids):
    with pytest.raises(ValueError):
        config.validate_character_list(ids)
```

기존 `test_valid_character` / `test_invalid_character_rejected` 블록은 삭제(`character_id` 단일 값 검증은 더 이상 필요 없음):

```python
# 삭제 대상
@pytest.mark.parametrize("ch", ["happy", "excited", "sleepy"])
def test_valid_character(ch):
    config.validate_character(ch)


def test_invalid_character_rejected():
    with pytest.raises(ValueError):
        config.validate_character("grumpy")
```

기존 `test_default_has_all_v2_fields` 안의 `assert c.character_id == "happy"` 줄은 아래로 교체:

```python
    assert c.active_character_ids == ["happy"]
```

- [ ] **Step 2: 실패 확인**

```
cd /c/Users/PC-55/water_timer
.venv/Scripts/pytest.exe tests/test_config.py -v 2>&1 | tail -20
```
기대: 신규 테스트들이 `AttributeError: module 'src.config' has no attribute 'validate_character_list'` 등으로 FAIL.

- [ ] **Step 3: `config.py` 스키마 변경 + 마이그레이션 + 검증 구현**

파일 `C:\Users\PC-55\water_timer\src\config.py` 를 아래 변경들로 업데이트:

1) **Config 데이터클래스에서 `character_id` 제거, `active_character_ids` 추가**

다음 줄(기존):

```python
    character_id: str = "happy"                 # 팝업 캐릭터: happy/excited/sleepy/custom
    character_image_paths: List[str] = field(default_factory=list)   # 사용자가 업로드한 이미지 전체 카탈로그
    active_image_paths: List[str] = field(default_factory=list)      # 'custom' 모드에서 랜덤 순환에 참여할 subset
```

로 바꿔서:

```python
    active_character_ids: List[str] = field(default_factory=lambda: ["happy"])  # 빌트인 캐릭터 활성 목록 (happy/excited/sleepy)
    character_image_paths: List[str] = field(default_factory=list)   # 사용자가 업로드한 이미지 전체 카탈로그
    active_image_paths: List[str] = field(default_factory=list)      # 업로드 이미지 활성 목록 (랜덤 풀 참여)
```

2) **`_default()` 함수 안에서 `character_id="happy"` 줄을 `active_character_ids=["happy"]` 로 교체**

기존:

```python
        character_id="happy",
        character_image_paths=[],
        active_image_paths=[],
```

로 바꿔서:

```python
        active_character_ids=["happy"],
        character_image_paths=[],
        active_image_paths=[],
```

3) **검증 함수 추가 (`validate_character` 는 그대로 남겨 유지 — 빌트인 id 단일 검사 기능은 내부에서 `validate_character_list`가 사용)**

기존 `validate_character` 함수는 그대로 두고, 바로 아래에 새 함수 추가:

```python
def validate_character_list(ids) -> None:
    if not isinstance(ids, list):
        raise ValueError("active_character_ids는 리스트여야 합니다")
    for cid in ids:
        if not isinstance(cid, str) or cid not in BUILTIN_CHARACTERS:
            raise ValueError(f"지원하지 않는 빌트인 캐릭터: {cid!r}")
```

4) **`_from_dict` 안 마이그레이션 로직 교체**

찾을 줄:

```python
        character_id=str(d.get("character_id", defaults.character_id)),
        character_image_paths=image_paths,
        active_image_paths=active_paths,
```

로 바꿔서:

```python
        active_character_ids=_migrate_character_ids(d, defaults.active_character_ids),
        character_image_paths=image_paths,
        active_image_paths=active_paths,
```

그리고 `_from_dict` 바로 위에 헬퍼 함수 추가:

```python
def _migrate_character_ids(d: dict, default: List[str]) -> List[str]:
    """v2/v3.x → v3.3 마이그레이션.

    - active_character_ids가 이미 있으면 그대로(유효한 값만 필터).
    - 없고 character_id가 빌트인이면 [character_id].
    - character_id='custom' 이면 빌트인은 전부 비활성 → [].
    - 둘 다 없으면 기본값.
    """
    if "active_character_ids" in d:
        return [cid for cid in d["active_character_ids"]
                if isinstance(cid, str) and cid in BUILTIN_CHARACTERS]
    legacy = d.get("character_id")
    if legacy in BUILTIN_CHARACTERS:
        return [legacy]
    if legacy == "custom":
        return []
    return list(default)
```

5) **`_validate` 함수의 캐릭터 검증 교체**

기존:

```python
    validate_character(c.character_id)
```

로 바꿔서:

```python
    validate_character_list(c.active_character_ids)
```

- [ ] **Step 4: 테스트 통과 확인**

```
.venv/Scripts/pytest.exe tests/test_config.py -v 2>&1 | tail -15
```
기대: 새 테스트들 모두 PASS + 기존 테스트 중 `character_id` 참조 삭제/수정된 것 PASS.

- [ ] **Step 5: 전체 suite 회귀 확인**

```
.venv/Scripts/pytest.exe tests/ -q
```
기대: 80 passed 전후 (기존 77 - 삭제된 2개 + 신규 추가 5개 = 80).

- [ ] **Step 6: 커밋**

```
git add src/config.py tests/test_config.py
git commit -m "feat(config): active_character_ids replaces single character_id

Schema:
- Remove character_id: str
- Add active_character_ids: list[str] (default ['happy']), subset of
  BUILTIN_CHARACTERS.

Migration (_from_dict): if legacy character_id is a builtin, lift into
list; if 'custom', start with empty builtin list (upload pool stays
separate via active_image_paths).

New validator validate_character_list accepts empty + any subset of
builtins.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: `app.py` 선택 로직 — `_pick_for_popup` 통합

**Files:**
- Modify: `src/app.py`

작업자 메모: 기존 `_pick_image` 는 업로드 이미지만 다뤘다. 이제 빌트인도 풀에 포함되므로 `_pick_for_popup` 이 `(kind, value)` 튜플을 반환하고, 호출측에서 Popup의 기존 파라미터 `character_id`/`character_image_path` 로 매핑한다.

- [ ] **Step 1: 상태 변수 이름 변경 + 선택 메서드 교체**

파일 `C:\Users\PC-55\water_timer\src\app.py` 에서 다음 찾을 줄:

```python
        self._last_message_index: Optional[int] = None
        self._last_image_path: Optional[str] = None
```

로 바꿔서:

```python
        self._last_message_index: Optional[int] = None
        self._last_pick: Optional[tuple] = None   # (kind, value) — 직전 팝업 캐릭터
```

- [ ] **Step 2: `_pick_image` 메서드 전체 교체**

기존 메서드(문서 문자열 포함) 전체:

```python
    def _pick_image(self) -> str:
        """character_id=='custom'일 때 활성 풀에서 랜덤 하나. 직전 것과 중복 회피."""
        paths = [p for p in self.cfg.active_image_paths if p]
        if not paths:
            return ""
        if len(paths) == 1:
            self._last_image_path = paths[0]
            return paths[0]
        candidates = [p for p in paths if p != self._last_image_path] or list(paths)
        chosen = random.choice(candidates)
        self._last_image_path = chosen
        return chosen
```

위 블록 전체를 아래로 교체:

```python
    def _pick_for_popup(self) -> tuple:
        """팝업에 보여줄 캐릭터 하나 선택.

        반환: (kind, value) 형태.
          - ("builtin", mood) — 내장 캐릭터 (mood in happy/excited/sleepy)
          - ("custom", image_path) — 업로드 이미지

        풀은 active_character_ids + active_image_paths. 둘 다 비면
        ("builtin", "happy") 로 fallback. 직전 선택과 중복 회피.
        """
        pool = [("builtin", cid) for cid in self.cfg.active_character_ids]
        pool += [("custom", p) for p in self.cfg.active_image_paths if p]
        if not pool:
            self._last_pick = ("builtin", "happy")
            return self._last_pick
        if len(pool) == 1:
            self._last_pick = pool[0]
            return pool[0]
        candidates = [x for x in pool if x != self._last_pick] or list(pool)
        chosen = random.choice(candidates)
        self._last_pick = chosen
        return chosen
```

- [ ] **Step 3: `show_popup` 안에서 선택 결과를 Popup 인자로 매핑**

찾을 블록:

```python
        image_path = ""
        if self.cfg.character_id == "custom":
            image_path = self._pick_image()
        self.active_popup = Popup(
            character_id=self.cfg.character_id,
            character_image_path=image_path,
            message=message,
```

로 바꿔서:

```python
        kind, value = self._pick_for_popup()
        if kind == "custom":
            popup_char_id = "custom"
            popup_image_path = value
        else:
            popup_char_id = value
            popup_image_path = ""
        self.active_popup = Popup(
            character_id=popup_char_id,
            character_image_path=popup_image_path,
            message=message,
```

- [ ] **Step 4: 날짜 전환 시 last_pick 초기화 — 이전과 같은 패턴 유지**

찾을 줄:

```python
            self.state = reloaded
            self._last_message_index = None
            self.tray.set_count(self.state.count)
```

로 바꿔서:

```python
            self.state = reloaded
            self._last_message_index = None
            self._last_pick = None
            self.tray.set_count(self.state.count)
```

- [ ] **Step 5: import·로드 확인**

```
cd /c/Users/PC-55/water_timer
.venv/Scripts/python.exe -c "from src.app import Application; print('ok')"
```
기대: `ok`

- [ ] **Step 6: 전체 회귀 테스트**

```
.venv/Scripts/pytest.exe tests/ -q
```
기대: 80 passed.

- [ ] **Step 7: 커밋**

```
git add src/app.py
git commit -m "feat(app): _pick_for_popup unifies builtin + custom pool random selection

Replaces _pick_image (custom-only). New method returns (kind, value)
tuple drawn from union of active_character_ids + active_image_paths,
avoiding the last-picked entry. show_popup maps kind to the existing
Popup character_id / character_image_path kwargs without changing
Popup's API.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: `settings_window.py` — `_CharacterCard` 토글형 + `_CustomPanel` 로직 갱신 + hint

**Files:**
- Modify: `src/settings_window.py`

작업자 메모: `_CharacterCard` 를 라디오에서 토글 방식으로 바꿔 여러 개를 동시에 활성화 가능하게. `_CustomPanel`의 `_rebuild_character_grid` / `_on_builtin_click` / 업로드 핸들러들은 새 스키마(`active_character_ids`)를 읽고 쓰도록. 섹션 hint 문구 업데이트.

- [ ] **Step 1: `_CharacterCard.on_click` 콜백 이름과 동작 정리 — 기능 의미는 토글로 바뀜 (시그니처는 유지, 호출측이 토글 처리)**

`_CharacterCard` 내부 코드는 **현재 그대로 유지한다**. (`on_click(char_id)` 콜백을 그대로 사용. 호출측이 active_character_ids 토글을 담당.)

클래스 상단 docstring만 살짝 업데이트해 의미 변경을 반영. 파일 `C:\Users\PC-55\water_timer\src\settings_window.py` 의 `_CharacterCard` 클래스 맨 위:

```python
class _CharacterCard(QFrame):
    """캐릭터 선택 카드. 그라디언트 배경 + Droplet + 이름 라벨."""
```

를:

```python
class _CharacterCard(QFrame):
    """캐릭터 선택 카드. 그라디언트 배경 + Droplet + 이름 라벨.

    on_click 콜백으로 해당 id를 넘긴다. 선택 상태는 외부(부모)가 관리하며
    set_selected() 로 반영해준다. 라디오가 아니라 토글처럼 사용 가능.
    """
```

- [ ] **Step 2: `_CustomPanel.__init__` 의 Section hint 업데이트**

기존:

```python
        # ---- 캐릭터 이미지 ----
        char_section = Section("캐릭터 이미지",
                               hint="팝업에 표시할 이미지를 선택하세요")
        root.addWidget(char_section)
```

로 바꿔서:

```python
        # ---- 캐릭터 ----
        char_section = Section(
            "캐릭터",
            hint="원하는 캐릭터·이미지를 여러 개 고르면 팝업마다 랜덤으로 나와요. "
                 "아무것도 안 고르면 기본 캐릭터가 나타나요.",
        )
        root.addWidget(char_section)
```

- [ ] **Step 3: `_rebuild_character_grid` 를 `active_character_ids` 기반 토글로 교체**

기존 메서드 전체:

```python
    def _rebuild_character_grid(self):
        """그리드를 현재 config 기준으로 다시 구성.

        - 빌트인 3종 + 업로드된 이미지들 + '+ 업로드' 카드.
        - 업로드 이미지는 active_image_paths에 포함됐는지에 따라 개별 선택 상태.
        - 활성 이미지가 하나 이상 있으면 character_id='custom' (팝업에서 랜덤 순환),
          아무것도 활성이 아니면 빌트인 모드로 복귀.
        """
        while self._char_grid_layout.count():
            item = self._char_grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        cfg = self._sw._cfg
        active_set = set(cfg.active_image_paths)
        is_custom_mode = (cfg.character_id == "custom" and bool(active_set))

        self._char_cards: list[_CharacterCard] = []
        self._user_cards: dict[str, _UserImageCard] = {}

        cards: list[QWidget] = []
        # 1) 빌트인 3종 — custom 모드가 아닐 때만 선택 표시
        for cid, name in CHARACTERS:
            c = _CharacterCard(cid, name,
                               selected=(cfg.character_id == cid and not is_custom_mode),
                               on_click=self._on_builtin_click)
            self._char_cards.append(c)
            cards.append(c)
        # 2) 업로드된 이미지들 — 각자 active 여부로 개별 선택 표시
        for p in cfg.character_image_paths:
            card = _UserImageCard(
                image_path=p,
                selected=(p in active_set),
                on_select=lambda pp=p: self._toggle_user_image(pp),
                on_remove=self._remove_user_image,
            )
            self._user_cards[p] = card
            cards.append(card)
        # 3) + 업로드
        cards.append(_AddUploadCard(on_pick_file=self._pick_file))

        cols = 4
        for i, card in enumerate(cards):
            r, c = divmod(i, cols)
            self._char_grid_layout.addWidget(card, r, c)
```

를 전체 교체:

```python
    def _rebuild_character_grid(self):
        """그리드를 현재 config 기준으로 다시 구성.

        빌트인 3종 + 업로드된 이미지들 + '+ 업로드' 카드. 모든 카드가 개별 토글.
        - 빌트인: active_character_ids 에 포함되면 선택 상태.
        - 업로드: active_image_paths 에 포함되면 선택 상태.
        """
        while self._char_grid_layout.count():
            item = self._char_grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        cfg = self._sw._cfg
        active_builtin_set = set(cfg.active_character_ids)
        active_image_set = set(cfg.active_image_paths)

        self._char_cards: list[_CharacterCard] = []
        self._user_cards: dict[str, _UserImageCard] = {}

        cards: list[QWidget] = []
        # 1) 빌트인 3종 — 각자 토글
        for cid, name in CHARACTERS:
            c = _CharacterCard(cid, name,
                               selected=(cid in active_builtin_set),
                               on_click=self._toggle_builtin)
            self._char_cards.append(c)
            cards.append(c)
        # 2) 업로드 이미지들
        for p in cfg.character_image_paths:
            card = _UserImageCard(
                image_path=p,
                selected=(p in active_image_set),
                on_select=lambda pp=p: self._toggle_user_image(pp),
                on_remove=self._remove_user_image,
            )
            self._user_cards[p] = card
            cards.append(card)
        # 3) + 업로드
        cards.append(_AddUploadCard(on_pick_file=self._pick_file))

        cols = 4
        for i, card in enumerate(cards):
            r, c = divmod(i, cols)
            self._char_grid_layout.addWidget(card, r, c)
```

- [ ] **Step 4: `_on_builtin_click` → `_toggle_builtin` 로 교체**

기존:

```python
    def _on_builtin_click(self, char_id: str):
        """빌트인 클릭 → 해당 빌트인 모드로 전환. active 선택은 유지(기억됨)."""
        self._sw._apply(character_id=char_id)
        self._rebuild_character_grid()
```

로 교체:

```python
    def _toggle_builtin(self, char_id: str):
        """빌트인 카드 클릭 → active_character_ids 에 토글."""
        active = list(self._sw._cfg.active_character_ids)
        if char_id in active:
            active.remove(char_id)
        else:
            active.append(char_id)
        self._sw._apply(active_character_ids=active)
        self._rebuild_character_grid()
```

- [ ] **Step 5: `_toggle_user_image` 수정 — `character_id` 참조 제거**

기존 메서드 전체:

```python
    def _toggle_user_image(self, path: str):
        """업로드 이미지 카드 클릭 → active 여부 개별 토글.

        - 활성이 하나 이상 있으면 character_id='custom'
        - 모두 비활성이면 character_id='happy' (빌트인 기본)로 복귀
        """
        cfg = self._sw._cfg
        active = list(cfg.active_image_paths)
        if path in active:
            active.remove(path)
        else:
            active.append(path)
        changes = {"active_image_paths": active}
        if active:
            changes["character_id"] = "custom"
        else:
            # 활성 이미지가 없으면 빌트인 모드로 복귀
            if cfg.character_id == "custom":
                changes["character_id"] = "happy"
        self._sw._apply(**changes)
        self._rebuild_character_grid()
```

로 교체:

```python
    def _toggle_user_image(self, path: str):
        """업로드 이미지 카드 클릭 → active_image_paths 에 토글."""
        active = list(self._sw._cfg.active_image_paths)
        if path in active:
            active.remove(path)
        else:
            active.append(path)
        self._sw._apply(active_image_paths=active)
        self._rebuild_character_grid()
```

- [ ] **Step 6: `_pick_file` 수정 — `character_id` 제거**

기존:

```python
    def _pick_file(self):
        from PySide6.QtWidgets import QFileDialog
        from src import character_image
        path, _ = QFileDialog.getOpenFileName(
            self, "캐릭터 이미지 선택", "",
            "이미지 (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
        )
        if not path:
            return
        saved_path = character_image.import_user_image(path)
        if not saved_path:
            QMessageBox.warning(self, "오류",
                                "이미지를 불러올 수 없습니다. 다른 파일을 선택해 주세요.")
            return
        pm = QPixmap(saved_path)
        if pm.isNull():
            character_image.clear_user_image(saved_path)
            QMessageBox.warning(self, "오류",
                                "지원하지 않는 이미지 형식입니다.")
            return
        # 업로드된 새 이미지는 카탈로그에 추가되고, 바로 active 로도 등록(편의).
        new_paths = list(self._sw._cfg.character_image_paths) + [saved_path]
        new_active = list(self._sw._cfg.active_image_paths) + [saved_path]
        self._sw._apply(
            character_image_paths=new_paths,
            active_image_paths=new_active,
            character_id="custom",
        )
        self._rebuild_character_grid()
```

마지막 `self._sw._apply(...)` 호출에서 `character_id="custom",` 줄만 삭제:

```python
        self._sw._apply(
            character_image_paths=new_paths,
            active_image_paths=new_active,
        )
        self._rebuild_character_grid()
```

- [ ] **Step 7: `_remove_user_image` 수정 — `character_id` 제거**

기존:

```python
    def _remove_user_image(self, path: str):
        from src import character_image
        new_paths = [p for p in self._sw._cfg.character_image_paths if p != path]
        new_active = [p for p in self._sw._cfg.active_image_paths if p != path]
        changes = {
            "character_image_paths": new_paths,
            "active_image_paths": new_active,
        }
        # 활성이 하나도 없으면 빌트인으로 되돌림
        if not new_active and self._sw._cfg.character_id == "custom":
            changes["character_id"] = "happy"
        self._sw._apply(**changes)
        character_image.clear_user_image(path)
        self._rebuild_character_grid()
```

로 교체:

```python
    def _remove_user_image(self, path: str):
        from src import character_image
        new_paths = [p for p in self._sw._cfg.character_image_paths if p != path]
        new_active = [p for p in self._sw._cfg.active_image_paths if p != path]
        self._sw._apply(
            character_image_paths=new_paths,
            active_image_paths=new_active,
        )
        character_image.clear_user_image(path)
        self._rebuild_character_grid()
```

- [ ] **Step 8: 스모크 체크 — 설정창 단독 로드**

```
cd /c/Users/PC-55/water_timer
.venv/Scripts/python.exe -c "
from PySide6.QtWidgets import QApplication
app = QApplication([])
from src import config as cm
from src.settings_window import SettingsWindow
cfg = cm._default()
dlg = SettingsWindow(cfg=cfg, current_count=3, on_save=lambda c: None, on_reset_count=lambda: None, on_add_cup=lambda: None)
print('ok')
"
```
기대: `ok`

- [ ] **Step 9: 회귀 테스트**

```
.venv/Scripts/pytest.exe tests/ -q
```
기대: 80 passed.

- [ ] **Step 10: 커밋**

```
git add src/settings_window.py
git commit -m "feat(settings): builtins toggle individually like uploaded images

Character section now treats all cards uniformly: clicking any card
(builtin or uploaded) toggles its entry in active_character_ids or
active_image_paths respectively. The pool is their union. Hint text
clarifies that picking multiple cards enables random rotation.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: PyInstaller 재빌드 + 수동 QA

**Files:** 변경 없음(빌드 산출물)

- [ ] **Step 1: 실행 중인 구버전 종료 + dist 정리**

```
cd /c/Users/PC-55/water_timer
tasklist //FI "IMAGENAME eq WaterTimer.exe" 2>&1 | grep WaterTimer | awk '{print $2}' | while read pid; do taskkill //PID $pid //F; done
sleep 1
rm -rf dist build
```

- [ ] **Step 2: 빌드**

```
.venv/Scripts/pyinstaller.exe build.spec 2>&1 | tail -3
```
기대: 마지막 줄 `Building EXE from EXE-00.toc completed successfully.`

- [ ] **Step 3: .exe 존재 확인**

```
ls -la dist/WaterTimer.exe
```
기대: ~45 MB 파일.

- [ ] **Step 4: 수동 QA (dist/WaterTimer.exe 더블클릭)**

다음 체크리스트 전부 통과하는지 확인:

- [ ] 트레이 아이콘 뜸
- [ ] 트레이 → "지금 바로 알림 보기" → 팝업 뜸
- [ ] 팝업 "마셨어요!" 클릭 → 카운트 증가 + 물방울 파티클(매끈한 teardrop 모양) → 페이드 아웃
- [ ] 팝업 "5분 뒤" 클릭 → 닫힘 (5분 후 자동 재알림)
- [ ] 팝업 "×" 클릭 → 즉시 닫힘
- [ ] 설정 → 🎨 커스터마이즈 → 빌트인 3종 전부 토글 ON → "지금 알림 보기" 여러 번 → happy/excited/sleepy 섞여 나옴
- [ ] 이미지 업로드 2장 이상 → 빌트인 1개 + 업로드 2장 토글 → 섞인 풀에서 랜덤
- [ ] 모든 카드 토글 OFF → "지금 알림 보기" → happy 로 fallback
- [ ] 팝업 뜨는 동안 작업표시줄에 WaterTimer 항목이 **잠깐** 보이는 것은 **정상** (Qt.Dialog 플래그 바꾼 대가)

- [ ] **Step 5: 커밋 (빌드 산출물은 .gitignore로 제외이므로 변경 없으면 스킵)**

```
git status
```
변경 없으면 커밋 생략.

---

## 변경 요약

끝나면 커밋 이력:
1. `fix(popup): use Qt.Dialog flag so tray-launched popup receives clicks`
2. `fix(popup): redraw particle with two cubic beziers for clean teardrop`
3. `feat(config): active_character_ids replaces single character_id`
4. `feat(app): _pick_for_popup unifies builtin + custom pool random selection`
5. `feat(settings): builtins toggle individually like uploaded images`
