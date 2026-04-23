"""알림음 재생. QSoundEffect 기반, 볼륨 반영.

사운드 id ("drop", "chime", "bubble", "soft", "off")에 대응하는 WAV 파일을
번들된 assets/sounds/에서 읽어 재생. "off"는 재생 자체를 건너뜀.

인스턴스 단위로 QSoundEffect를 재사용해 재생 지연을 최소화.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect


def _assets_base() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets"
    return Path(__file__).resolve().parent / "assets"


def sound_file_for(sound_id: str) -> Path:
    return _assets_base() / "sounds" / f"{sound_id}.wav"


class SoundPlayer:
    """QSoundEffect 풀. id별로 한 번 로드해 재사용."""

    def __init__(self):
        self._effects: Dict[str, QSoundEffect] = {}

    def _get(self, sound_id: str) -> QSoundEffect:
        fx = self._effects.get(sound_id)
        if fx is None:
            fx = QSoundEffect()
            path = sound_file_for(sound_id)
            if path.exists():
                fx.setSource(QUrl.fromLocalFile(str(path)))
            self._effects[sound_id] = fx
        return fx

    def play(self, sound_id: str, volume: int) -> None:
        """sound_id를 volume(0~100)으로 재생.

        "off"거나 파일이 없거나 로딩 실패면 아무것도 안 함.
        """
        if not sound_id or sound_id == "off":
            return
        fx = self._get(sound_id)
        if fx.status() == QSoundEffect.Error:
            return
        fx.setVolume(max(0.0, min(1.0, volume / 100.0)))
        fx.play()

    def stop(self, sound_id: str) -> None:
        fx = self._effects.get(sound_id)
        if fx is not None:
            fx.stop()
