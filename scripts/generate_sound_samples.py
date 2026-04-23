"""알림음 5종 WAV 파일 합성.

`src/assets/sounds/{id}.wav`에 저장. stdlib만 쓰므로 추가 의존성 없음.
소리 디자인은 각각:
  drop   — 고음 → 저음으로 떨어지는 물방울 '플링크'
  chime  — 짧은 2음 차임 (C6 + E6)
  bubble — 연속 작은 방울 3번
  soft   — 부드럽게 페이드 되는 저주파 사인
  off    — 무음 (0.1초 빈 파일, 재생해도 소리 안 남)

모두 0.6~1.0초 이하의 짧은 샘플.
"""
from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

SR = 44100           # 샘플 레이트
AMP = 0.35           # 기본 진폭 (클리핑 방지, 0~1)
OUT_DIR = Path(__file__).resolve().parents[1] / "src" / "assets" / "sounds"


def _write_wav(path: Path, samples: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)   # int16
        w.setframerate(SR)
        data = bytearray()
        for s in samples:
            v = max(-1.0, min(1.0, s))
            data += struct.pack("<h", int(v * 32767))
        w.writeframes(bytes(data))


def _envelope(n: int, attack: float = 0.01, release: float = 0.2) -> list[float]:
    """짧은 어택/릴리즈 엔벨로프. attack/release는 초 단위."""
    env = [0.0] * n
    a = max(1, int(attack * SR))
    r = max(1, int(release * SR))
    for i in range(n):
        if i < a:
            env[i] = i / a
        elif i > n - r:
            env[i] = max(0.0, (n - i) / r)
        else:
            env[i] = 1.0
    return env


def sound_drop() -> list[float]:
    """물방울 플링크: 1800Hz → 400Hz로 미끄러지며 빠르게 감쇠."""
    dur = 0.35
    n = int(dur * SR)
    env = _envelope(n, attack=0.005, release=0.28)
    samples = []
    for i in range(n):
        t = i / SR
        # 주파수 슬라이드 (exp decay)
        f = 400 + (1800 - 400) * math.exp(-t * 12)
        phase = 2 * math.pi * f * t
        s = math.sin(phase) * env[i] * AMP
        samples.append(s)
    return samples


def sound_chime() -> list[float]:
    """2음 차임: C6(1047Hz) 그리고 E6(1319Hz) 겹쳐 울림."""
    dur = 0.8
    n = int(dur * SR)
    env = _envelope(n, attack=0.01, release=0.6)
    samples = []
    for i in range(n):
        t = i / SR
        s = 0.0
        # 첫 음 즉시, 둘째 음 약간 뒤
        if t >= 0.0:
            s += math.sin(2 * math.pi * 1047 * t) * 0.5
        if t >= 0.15:
            s += math.sin(2 * math.pi * 1319 * (t - 0.15)) * 0.5
        samples.append(s * env[i] * AMP)
    return samples


def sound_bubble() -> list[float]:
    """뽀글뽀글: 0.15초 간격으로 짧은 고주파 펄스 3개."""
    dur = 0.55
    n = int(dur * SR)
    samples = [0.0] * n
    for pulse, start in enumerate([0.0, 0.15, 0.30]):
        freq = 900 + pulse * 200   # 음높이 살짝 다르게
        p_dur = 0.1
        p_n = int(p_dur * SR)
        p_start = int(start * SR)
        env_p = _envelope(p_n, attack=0.005, release=0.08)
        for i in range(p_n):
            idx = p_start + i
            if idx >= n:
                break
            t = i / SR
            samples[idx] += math.sin(2 * math.pi * freq * t) * env_p[i] * AMP * 0.9
    return samples


def sound_soft() -> list[float]:
    """부드러운 저주파 사인 페이드 인/아웃."""
    dur = 0.9
    n = int(dur * SR)
    samples = []
    for i in range(n):
        t = i / SR
        # 저주파 두 층 겹침: 440Hz + 660Hz (3:2 배음)
        s = (math.sin(2 * math.pi * 440 * t) * 0.55
             + math.sin(2 * math.pi * 660 * t) * 0.35)
        # 긴 어택/릴리즈
        if t < 0.3:
            env = t / 0.3
        elif t > dur - 0.4:
            env = max(0.0, (dur - t) / 0.4)
        else:
            env = 1.0
        samples.append(s * env * AMP * 0.85)
    return samples


def sound_off() -> list[float]:
    """무음 — 빈 WAV. 재생해도 소리 안 남."""
    return [0.0] * int(0.05 * SR)


def main():
    generators = {
        "drop":   sound_drop,
        "chime":  sound_chime,
        "bubble": sound_bubble,
        "soft":   sound_soft,
        "off":    sound_off,
    }
    for sid, gen in generators.items():
        out = OUT_DIR / f"{sid}.wav"
        _write_wav(out, gen())
        print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
