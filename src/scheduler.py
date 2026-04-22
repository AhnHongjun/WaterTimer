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
