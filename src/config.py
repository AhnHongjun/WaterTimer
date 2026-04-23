"""config.json — 사용자 설정.

스키마 변경 시: DEFAULT_CONFIG 업데이트 + migration 코드 추가.
손상/누락 시 자동 복구 + .bak 백업.
"""
from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass, asdict, field, replace as dc_replace
from typing import List, Optional

from src import paths


VALID_POSITIONS = {"bottom_right", "bottom_left", "top_right", "top_left", "center"}
# 내장 캐릭터 3종 + "custom" (character_image_path를 사용)
BUILTIN_CHARACTERS = {"happy", "excited", "sleepy"}
VALID_CHARACTERS = BUILTIN_CHARACTERS | {"custom"}
VALID_SOUNDS = {"drop", "chime", "bubble", "soft", "off"}
VALID_CLOSE_BEHAVIORS = {"tray", "quit", "ask"}

MIN_INTERVAL = 1
MAX_INTERVAL = 1440       # 24h
MIN_AUTO_CLOSE = 0        # 0 = "닫지 않음" (v2). 기존 코드와 호환을 위해 하한 완화.
MAX_AUTO_CLOSE = 600      # 10분까지 허용 (기존 60 → 600으로 확장)
MIN_GOAL = 1
MAX_GOAL = 16
MIN_VOLUME = 0
MAX_VOLUME = 100
MIN_SNOOZE = 1
MAX_SNOOZE = 60
ALL_DAYS = [0, 1, 2, 3, 4, 5, 6]   # 0 = 월요일

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
    # ---- 기존 필드 (v1, 유지) ----
    interval_minutes: int
    active_start: str           # "HH:MM"
    active_end: str             # "HH:MM"
    popup_position: str
    auto_close_seconds: int
    autostart: bool
    sets: List[Set]             # legacy: 이미지+메시지 세트. v2부터는 읽기 전용으로 유지.

    # ---- v2 신규 필드 ----
    goal: int = 8                               # 하루 목표 잔 수
    days: List[int] = field(default_factory=lambda: list(ALL_DAYS))  # 알림 요일 (0=월)
    active_character_ids: List[str] = field(default_factory=lambda: ["happy"])  # 빌트인 캐릭터 활성 목록 (happy/excited/sleepy)
    character_image_paths: List[str] = field(default_factory=list)   # 사용자가 업로드한 이미지 전체 카탈로그
    active_image_paths: List[str] = field(default_factory=list)      # 업로드 이미지 활성 목록 (랜덤 풀 참여)
    messages: List[str] = field(default_factory=list)                # 알림 메시지 (평면 목록)
    snooze_minutes: int = 5                     # "5분 뒤" 스누즈 분
    sound_enabled: bool = False
    sound_name: str = "drop"
    volume: int = 60
    minimize_on_start: bool = False
    tray_icon: bool = True
    close_behavior: str = "tray"


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
        goal=8,
        days=list(ALL_DAYS),
        active_character_ids=["happy"],
        character_image_paths=[],
        active_image_paths=[],
        messages=list(DEFAULT_MESSAGES),
        snooze_minutes=5,
        sound_enabled=False,
        sound_name="drop",
        volume=60,
        minimize_on_start=False,
        tray_icon=True,
        close_behavior="tray",
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


def validate_character(c: str) -> None:
    if c not in VALID_CHARACTERS:
        raise ValueError(f"지원하지 않는 캐릭터: {c}")


def validate_character_list(ids) -> None:
    if not isinstance(ids, list):
        raise ValueError("active_character_ids는 리스트여야 합니다")
    for cid in ids:
        if not isinstance(cid, str) or cid not in BUILTIN_CHARACTERS:
            raise ValueError(f"지원하지 않는 빌트인 캐릭터: {cid!r}")


def validate_sound(name: str) -> None:
    if name not in VALID_SOUNDS:
        raise ValueError(f"지원하지 않는 알림음: {name}")


def validate_close_behavior(b: str) -> None:
    if b not in VALID_CLOSE_BEHAVIORS:
        raise ValueError(f"지원하지 않는 닫기 동작: {b}")


def validate_goal(g: int) -> None:
    if not isinstance(g, int) or g < MIN_GOAL or g > MAX_GOAL:
        raise ValueError(f"목표는 {MIN_GOAL}~{MAX_GOAL}잔 사이여야 합니다")


def validate_volume(v: int) -> None:
    if not isinstance(v, int) or v < MIN_VOLUME or v > MAX_VOLUME:
        raise ValueError(f"볼륨은 {MIN_VOLUME}~{MAX_VOLUME} 사이여야 합니다")


def validate_snooze(m: int) -> None:
    if not isinstance(m, int) or m < MIN_SNOOZE or m > MAX_SNOOZE:
        raise ValueError(f"스누즈는 {MIN_SNOOZE}~{MAX_SNOOZE}분 사이여야 합니다")


def validate_days(ds) -> None:
    if not isinstance(ds, list):
        raise ValueError("요일 목록은 리스트여야 합니다")
    for d in ds:
        if not isinstance(d, int) or d < 0 or d > 6:
            raise ValueError(f"잘못된 요일: {d} (0~6이어야 함)")


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


def _from_dict(d: dict) -> Config:
    """파일에서 읽은 dict → Config.

    누락된 신규 필드는 기본값으로 채움(무손실 마이그레이션).
    기존 JSON에 messages 필드가 없으면 sets에서 유도.
    """
    defaults = _default()
    sets = [Set(**s) for s in d.get("sets", [])]
    messages = d.get("messages")
    if messages is None:
        # v1 → v2 마이그레이션: 기존 세트의 메시지를 평면 목록으로 복사
        messages = [s.message for s in sets] or list(DEFAULT_MESSAGES)
    # v3 → v3.1 마이그레이션: character_image_path(단일) → character_image_paths(리스트)
    image_paths = d.get("character_image_paths")
    if image_paths is None:
        legacy = str(d.get("character_image_path", ""))
        image_paths = [legacy] if legacy else []
    image_paths = [str(p) for p in image_paths if p]
    # v3.1 → v3.2 마이그레이션: active_image_paths 누락이면 전체를 활성으로 취급.
    active_paths = d.get("active_image_paths")
    if active_paths is None:
        active_paths = list(image_paths)
    # active 는 카탈로그 내에 있는 것만 유지
    active_paths = [p for p in active_paths if p in image_paths]
    return Config(
        interval_minutes=int(d["interval_minutes"]),
        active_start=str(d["active_start"]),
        active_end=str(d["active_end"]),
        popup_position=str(d["popup_position"]),
        auto_close_seconds=int(d["auto_close_seconds"]),
        autostart=bool(d["autostart"]),
        sets=sets,
        goal=int(d.get("goal", defaults.goal)),
        days=list(d.get("days", defaults.days)),
        active_character_ids=_migrate_character_ids(d, defaults.active_character_ids),
        character_image_paths=image_paths,
        active_image_paths=active_paths,
        messages=list(messages),
        snooze_minutes=int(d.get("snooze_minutes", defaults.snooze_minutes)),
        sound_enabled=bool(d.get("sound_enabled", defaults.sound_enabled)),
        sound_name=str(d.get("sound_name", defaults.sound_name)),
        volume=int(d.get("volume", defaults.volume)),
        minimize_on_start=bool(d.get("minimize_on_start", defaults.minimize_on_start)),
        tray_icon=bool(d.get("tray_icon", defaults.tray_icon)),
        close_behavior=str(d.get("close_behavior", defaults.close_behavior)),
    )


def _validate(c: Config) -> None:
    validate_interval_minutes(c.interval_minutes)
    validate_auto_close(c.auto_close_seconds)
    validate_position(c.popup_position)
    validate_active_window(c.active_start, c.active_end)
    validate_goal(c.goal)
    validate_days(c.days)
    validate_character_list(c.active_character_ids)
    validate_sound(c.sound_name)
    validate_volume(c.volume)
    validate_snooze(c.snooze_minutes)
    validate_close_behavior(c.close_behavior)


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
        # 누락 필드를 채워 넣었다면 즉시 디스크에 다시 써서 마이그레이션 완료
        save(c)
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


# ---------- 메시지 목록 헬퍼 (v2) ----------

def add_message(c: Config, text: str) -> Config:
    return dc_replace(c, messages=list(c.messages) + [text])


def remove_message(c: Config, index: int) -> Config:
    new_msgs = list(c.messages)
    if 0 <= index < len(new_msgs):
        del new_msgs[index]
    return dc_replace(c, messages=new_msgs)


def update_message(c: Config, index: int, text: str) -> Config:
    new_msgs = list(c.messages)
    if 0 <= index < len(new_msgs):
        new_msgs[index] = text
    return dc_replace(c, messages=new_msgs)
