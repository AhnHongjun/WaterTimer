"""today.json — 오늘의 카운터 + 마지막 알림 시각 + 최근 N일 기록.

날짜가 바뀌면 load() 시점에 자동으로 리셋되고, 전날 카운트는 history에 푸시된다.
파일이 손상되면 기본값으로 복구하고 손상본을 .bak으로 백업한다.
"""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, asdict, field
from datetime import datetime, date
from typing import List, Optional

from src import paths

HISTORY_MAX_DAYS = 30  # 차트·통계용으로 최근 30일만 보관


@dataclass
class DayRecord:
    date: str   # "YYYY-MM-DD"
    count: int


@dataclass
class State:
    date: str                                # "YYYY-MM-DD"
    count: int
    last_notified_at: Optional[datetime]     # None 또는 datetime
    history: List[DayRecord] = field(default_factory=list)


def _today_str() -> str:
    return date.today().isoformat()


def _default() -> State:
    return State(date=_today_str(), count=0, last_notified_at=None, history=[])


def _to_dict(s: State) -> dict:
    return {
        "date": s.date,
        "count": s.count,
        "last_notified_at": s.last_notified_at.isoformat() if s.last_notified_at else None,
        "history": [asdict(d) for d in s.history],
    }


def _from_dict(d: dict) -> State:
    last = d.get("last_notified_at")
    raw_hist = d.get("history", [])
    history = [DayRecord(date=str(x["date"]), count=int(x["count"])) for x in raw_hist]
    return State(
        date=d["date"],
        count=int(d["count"]),
        last_notified_at=datetime.fromisoformat(last) if last else None,
        history=history,
    )


def _rollover(old: State) -> State:
    """전날 상태를 history에 추가하고 오늘용 기본 상태로 교체."""
    new_history = list(old.history)
    # 오늘 이전 기록만 히스토리에 남김 (이미 있는 같은 날짜면 덮어쓰기)
    existing_dates = {r.date for r in new_history}
    if old.date not in existing_dates:
        new_history.append(DayRecord(date=old.date, count=old.count))
    # 최근 HISTORY_MAX_DAYS만 유지
    new_history = new_history[-HISTORY_MAX_DAYS:]
    return State(date=_today_str(), count=0, last_notified_at=None, history=new_history)


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
    # 날짜 전환 처리: 전날 카운트를 history에 축적
    if loaded.date != _today_str():
        s = _rollover(loaded)
        save(s)
        return s
    return loaded


def save(s: State) -> None:
    path = paths.state_path()
    path.write_text(json.dumps(_to_dict(s), ensure_ascii=False, indent=2), encoding="utf-8")


def increment_count(s: State) -> State:
    s2 = State(date=s.date, count=s.count + 1,
               last_notified_at=s.last_notified_at, history=s.history)
    save(s2)
    return s2


def update_last_notified(s: State, when: datetime) -> State:
    s2 = State(date=s.date, count=s.count,
               last_notified_at=when, history=s.history)
    save(s2)
    return s2
