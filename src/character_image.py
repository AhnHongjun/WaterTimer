"""사용자 캐릭터 이미지 import/clear 유틸.

사용자가 고른 파일을 %APPDATA%\\WaterTimer\\characters\\에 복사하고 그 복사본
경로를 돌려준다. 원본 파일이 이동·삭제돼도 앱에서 계속 쓸 수 있게 하기 위함.
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Optional

from src import paths


SUPPORTED_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


def import_user_image(source: str) -> Optional[str]:
    """source 경로의 이미지를 복사해 저장. 성공 시 절대 경로 문자열, 실패 시 None.

    확장자 검사만 하고 Qt가 실제로 로드 가능한지는 호출측에서 QPixmap으로 확인.
    """
    p = Path(source)
    if not p.exists() or not p.is_file():
        return None
    ext = p.suffix.lower()
    if ext not in SUPPORTED_EXT:
        return None
    dest_dir = paths.characters_dir()
    # 충돌 방지를 위해 유니크 파일명 사용 (원본 이름은 무시)
    dest = dest_dir / f"user_{uuid.uuid4().hex[:10]}{ext}"
    try:
        shutil.copy2(p, dest)
    except OSError:
        return None
    return str(dest)


def clear_user_image(path: str) -> None:
    """저장된 캐릭터 이미지 삭제. 우리 디렉터리 안의 파일만 삭제."""
    if not path:
        return
    p = Path(path)
    try:
        p_real = p.resolve()
        chars_real = paths.characters_dir().resolve()
        if chars_real in p_real.parents:
            p_real.unlink(missing_ok=True)
    except OSError:
        pass
