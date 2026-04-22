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
