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
