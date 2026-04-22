"""임시 placeholder 이미지 5장 + 앱 아이콘 .ico 생성.

사용자가 진짜 이미지를 주면 같은 파일명으로 덮어쓰기만 하면 된다.
PySide6의 QPixmap/QPainter를 쓰면 이미지 라이브러리 추가 의존 없이 처리 가능.
"""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap, QIcon, QImage
from PySide6.QtWidgets import QApplication

BASE = Path(__file__).resolve().parents[1] / "src" / "assets"
BUNDLED = BASE / "bundled"

COLORS = ["#4FC3F7", "#81D4FA", "#4DD0E1", "#80DEEA", "#29B6F6"]


def draw_drop(path: Path, color_hex: str, label: str, size: int = 256):
    pm = QPixmap(size, size)
    pm.fill(QColor(color_hex))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QColor("white"))
    font = QFont()
    font.setPointSize(80)
    p.setFont(font)
    p.drawText(pm.rect(), Qt.AlignCenter, "💧")
    font2 = QFont()
    font2.setPointSize(22)
    p.setFont(font2)
    p.drawText(pm.rect().adjusted(0, 160, 0, 0), Qt.AlignHCenter | Qt.AlignTop, label)
    p.end()
    pm.save(str(path), "PNG")


def main():
    app = QApplication([])
    BUNDLED.mkdir(parents=True, exist_ok=True)
    for i, color in enumerate(COLORS, start=1):
        draw_drop(BUNDLED / f"img{i}.png", color, f"#{i}")
    # 아이콘: 64x64 PNG → QIcon → .ico 저장
    icon_pm = QPixmap(64, 64)
    icon_pm.fill(QColor("#4FC3F7"))
    p = QPainter(icon_pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QColor("white"))
    font = QFont()
    font.setPointSize(28)
    p.setFont(font)
    p.drawText(icon_pm.rect(), Qt.AlignCenter, "💧")
    p.end()
    icon_pm.save(str(BASE / "icon.ico"), "ICO")
    print("생성 완료:", BUNDLED, BASE / "icon.ico")


if __name__ == "__main__":
    main()
