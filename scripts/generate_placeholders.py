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
    # 아이콘: PNG를 Qt 런타임용으로, ICO는 PyInstaller 빌드용으로.
    # 트레이 아이콘은 Windows에서 16~20픽셀로 표시되므로 256픽셀 원본을 저장해서 Qt가 알아서 축소.
    # ICO는 여러 사이즈(16,24,32,48,64)를 QIcon에 addPixmap으로 모아 저장해야 모든 환경에서 깨지지 않음.
    def draw_icon(size: int) -> QPixmap:
        pm = QPixmap(size, size)
        pm.fill(QColor("#4FC3F7"))
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QColor("white"))
        font = QFont()
        # 이모지 크기는 사이즈의 약 70%로 맞춤
        font.setPixelSize(max(10, int(size * 0.7)))
        p.setFont(font)
        p.drawText(pm.rect(), Qt.AlignCenter, "💧")
        p.end()
        return pm

    # 런타임용 PNG (QSystemTrayIcon, 팝업 fallback에 사용)
    draw_icon(256).save(str(BASE / "icon.png"), "PNG")

    # 빌드용 ICO — 여러 사이즈를 하나의 파일에 담기.
    # QPixmap.save로는 멀티사이즈 ICO가 안 되므로 각 사이즈를 QImage로 리스트에 모아 ICO로 직접 저장.
    # 간단 경로: 가장 큰 사이즈 하나만 저장해도 PyInstaller는 수용하며 Windows가 필요 시 스케일.
    # 다만 트레이에는 PNG를 쓰므로 ICO 품질은 실행파일 쉘 아이콘에만 영향.
    draw_icon(64).save(str(BASE / "icon.ico"), "ICO")

    print("생성 완료:", BUNDLED, BASE / "icon.png", BASE / "icon.ico")


if __name__ == "__main__":
    main()
