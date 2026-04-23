# Popup Fix + 캐릭터 멀티 선택 — 설계 문서

작성일: 2026-04-23
작성자: Claude (브레인스토밍 세션 기반)
상태: 초안 → 사용자 검토 대기

---

## 1. 한 줄 요약

팝업 클릭 불가 버그 수정 + "마셨어요!" 파티클 모양 정상화 + 빌트인 캐릭터(기본/신남/졸림)도 업로드 이미지처럼 개별 토글해 여러 개를 랜덤 풀에 섞을 수 있도록 한다.

## 2. 배경

현재 v3.2 상태 기준 세 가지 문제가 남아 있다:

1. **팝업 버튼 클릭 무반응**: 풀 앱(트레이 기반) 컨텍스트에서 팝업이 뜰 때 `Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint` 조합이 Windows에서 입력 활성화를 제대로 받지 못해 마우스 이벤트가 도달하지 않는다. `smoke_popup.py`에서는 문제없이 동작함(트레이 앱 컨텍스트가 아니기 때문).
2. **파티클 모양 깨짐**: "마셨어요!" 클릭 시 튀어오르는 물방울 10개가 작은 사이즈(8~12px)에서 이상한 모양으로 렌더됨. 원인은 SVG 원본 경로를 `QRect`(정수 좌표)로 직역해 호 시작점과 이전 베지어 종단점이 어긋나는 것.
3. **빌트인 단일 선택의 비대칭**: 업로드 이미지는 개별 토글(`active_image_paths`)로 여러 장을 랜덤 풀에 넣을 수 있지만, 빌트인 3종은 라디오 방식이라 하나만 골라진다. 사용자는 둘의 규칙이 같기를 원함.

## 3. 대상 사용자

기존 Water Timer 사용자(본인 + 선물 대상). 코드 유지보수는 Claude 담당. 비전공자에게 체감되는 동작 기준으로 설계.

## 4. 기능 요구사항

### 4.1 팝업 클릭 정상화
- 트레이 메뉴에서 "지금 바로 알림 보기" 클릭했을 때도 / 자동 알림 발화 시에도 팝업의 **"마셨어요!" / "5분 뒤" / ✕** 버튼이 바로 클릭 가능해야 함.
- 해결책: 팝업 창 플래그를 `Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint` → `Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint`로 변경.
- 트레이드오프: 팝업이 떠있는 동안(최대 12초) Windows 작업표시줄에 잠깐 항목이 뜸 — 허용.
- `showEvent`의 `self.raise_() + self.activateWindow()`는 유지(무해하고 포커스 안정성에 도움).

### 4.2 파티클 모양 정상화
- "마셨어요!" 버튼 클릭 시 캐릭터 위로 튀어오르는 10개의 파티클이 **매끈한 물방울 형태**여야 함.
- `_DropParticle.paintEvent`의 경로를 `QRect` 기반 호에서 2개 cubic 곡선으로 재구성:
  ```
  path.moveTo(cx, 0)
  path.cubicTo(w, h*0.45, w, h*0.75, cx, h)    # 우측 위→아래
  path.cubicTo(0, h*0.75, 0, h*0.45, cx, 0)    # 좌측 아래→위
  path.closeSubpath()
  ```
- 크기 8~12px에서도 안정적으로 렌더.

### 4.3 캐릭터 멀티 선택
- 🎨 커스터마이즈 탭에서 빌트인 3종(기본/신남/졸림)과 업로드 이미지 N장을 **동일 규칙으로 개별 토글** 가능.
- 선택된 항목 = 랜덤 풀에 참여. 팝업이 뜰 때마다 풀에서 직전 것과 다른 항목을 무작위로 고른다.
- 빌트인과 업로드 이미지가 한 풀에서 섞일 수 있음. 예: [기본, 졸림, 이미지A] 셋 다 토글 ON 상태면 3개 중 랜덤.
- 아무것도 선택 안 한 상태면 팝업 발화 시 **"기본" (happy) 로 fallback**. 설정 UI에 짧은 힌트로 안내.

## 5. 데이터 모델 변경

### 5.1 제거
- `character_id: str` — 단일 선택 개념 폐기.

### 5.2 추가/유지
- `active_character_ids: list[str]` — 활성 빌트인 목록. 값 범위: `{"happy", "excited", "sleepy"}`의 부분집합. 기본값 `["happy"]`.
- `active_image_paths: list[str]` — 활성 업로드 이미지 경로 목록 (변경 없음).
- `character_image_paths: list[str]` — 업로드 이미지 전체 카탈로그 (변경 없음).

### 5.3 마이그레이션

`_from_dict`에서:
- `active_character_ids`가 없으면 기존 `character_id`로부터 유도
  - `character_id == "happy" | "excited" | "sleepy"` → `[character_id]`
  - `character_id == "custom"` 또는 부재 → `[]`
- 기존 `character_id` 키는 무시(읽지 않음).

### 5.4 검증
- `validate_character_id` → `validate_character_list(ids: list[str])` 로 대체 (부분집합 검증, 빈 리스트 허용).

## 6. 선택 로직

### 6.1 app.py 내부 상태
- `_last_pick: Optional[tuple[str, str]]` — 최근 뽑은 항목. 튜플 첫 요소는 `"builtin"` / `"custom"`, 둘째는 mood id 또는 이미지 경로. 연속 중복 회피용.

### 6.2 `_pick_for_popup() -> tuple[str, str]`

```
pool = [("builtin", cid) for cid in cfg.active_character_ids]
     + [("custom", path) for path in cfg.active_image_paths]
if not pool:
    return ("builtin", "happy")
candidates = [x for x in pool if x != self._last_pick] or pool
chosen = random.choice(candidates)
self._last_pick = chosen
return chosen
```

### 6.3 Popup 호출 매핑

선택 결과를 현재 Popup API에 매핑:
- `("builtin", mood)` → `character_id=mood, character_image_path=""`
- `("custom", path)` → `character_id="custom", character_image_path=path`

`Popup.__init__`의 시그니처와 `_CharacterPanel`의 분기 로직은 **변경 없음**. `character_id`가 Popup 파라미터로 남아 있지만 Config에서는 제거되므로, app.py가 매 호출마다 위 매핑으로 채워준다.

## 7. UI 변경 (🎨 커스터마이즈 탭)

### 7.1 빌트인 카드
- `_CharacterCard` — 기존 단일 클릭 on_click 방식에서 **토글** 방식으로 변경.
- 선택 여부 판정: `cid in cfg.active_character_ids`.
- 시각: 업로드 이미지 카드와 동일하게 선택됨 = sky-500 2px 테두리.

### 7.2 클릭 동작
- 빌트인 카드 클릭 → 해당 id를 `active_character_ids`에 토글. 변경 즉시 저장.
- 업로드 카드 클릭 → 해당 경로를 `active_image_paths`에 토글. 동작 변경 없음(기존과 동일).
- 업로드 카드 × 삭제 → 카탈로그·active 양쪽에서 제거(기존과 동일).

### 7.3 힌트
- Section 제목 아래 hint 문구: "원하는 캐릭터·이미지를 여러 개 고르면 팝업마다 랜덤으로 나와요. 아무것도 안 고르면 기본 캐릭터가 나타나요."

## 8. 영향을 받는 파일

| 파일 | 변경 내용 |
|---|---|
| `src/popup.py` | 창 플래그 `Qt.Tool` → `Qt.Dialog`. `_DropParticle.paintEvent` 경로 재작성. |
| `src/config.py` | `character_id` 필드 제거. `active_character_ids` 추가 + 마이그레이션 + 검증. |
| `src/app.py` | `_pick_image` → `_pick_for_popup`로 확장. `_last_image_path` → `_last_pick`. `show_popup`에서 반환값을 popup 인자로 매핑. |
| `src/settings_window.py` | `_CharacterCard`를 토글형으로. `_CustomPanel._on_builtin_click` → `_toggle_builtin`. `_rebuild_character_grid`에서 선택 상태를 `active_character_ids` 기준으로. hint 문구 추가. |
| `tests/test_config.py` | `character_id` 기반 테스트를 `active_character_ids` 기반으로 수정. 마이그레이션 테스트 케이스 추가. |

## 9. 에러 처리

- 모든 활성 선택이 비어 있을 때: `_pick_for_popup`이 `("builtin", "happy")` fallback. 사용자에게 별도 경고 없음(설정 UI의 hint 문구로 안내).
- `active_character_ids`에 알려지지 않은 값이 들어있는 경우: `_validate`에서 예외 → 손상 복구 루프에서 기본값으로 리셋.

## 10. 테스트 전략

### 10.1 기존 유닛 테스트 조정
- `test_config.py`의 `character_id` 참조 삭제·수정.
- 새 테스트:
  - `test_migrates_builtin_character_id_to_list` — 기존 `character_id="sleepy"` → `active_character_ids=["sleepy"]`
  - `test_migrates_custom_character_id_to_empty_builtin_list` — 기존 `character_id="custom"` → `active_character_ids=[]`
  - `test_validate_character_list_accepts_subset`
  - `test_validate_character_list_rejects_unknown`

### 10.2 스모크 테스트
- `python -m scripts.smoke_popup` — 팝업 단독 시각 확인(파티클 모양).
- `python -m src.app` 실행 후 트레이 메뉴로 팝업 반복 띄우기, 빌트인 여러 개 토글 후 풀 검증.

### 10.3 수동 회귀
- 77개 유닛 테스트 통과 유지.
- PyInstaller 재빌드 후 .exe 실행 → 클릭 반응, 파티클 모양, 멀티 선택 UI 확인.

## 11. v1 스코프에서 제외한 것

- 파티클 수·위치·색상의 사용자 커스터마이징 (YAGNI)
- 캐릭터별 가중치(자주 나오게 설정) (YAGNI)
- 팝업 애니메이션 타이밍 조정 UI

## 12. 오픈 이슈

없음. 위 설계로 모든 요구사항 커버됨.
