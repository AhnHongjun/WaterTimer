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
