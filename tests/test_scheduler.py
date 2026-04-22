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
