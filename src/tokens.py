"""디자인 토큰: 색상, 타이포, 라디우스, 그림자, 간격.

`design_ref/styles.css`의 수치를 그대로 가져왔다. UI 코드에서는 이 상수를 참조해
Qt 스타일시트 문자열을 만들거나 QPainter로 직접 그린다.
"""
from __future__ import annotations

# ---------- Colors ----------
# 배경
BG = "#f4f8fc"
BG_2 = "#eaf2f8"
SURFACE = "#ffffff"
SURFACE_2 = "#f6fafd"

# Sky scale (primary)
SKY_50 = "#eaf4fc"
SKY_100 = "#d4e8f7"
SKY_200 = "#b3d6ef"
SKY_300 = "#8cc0e6"
SKY_400 = "#5fa8db"
SKY_500 = "#4a95d0"   # Primary
SKY_600 = "#3580bf"
SKY_700 = "#27669e"
SKY_800 = "#1a3550"

# Lines
LINE = "#e6eef6"
LINE_2 = "#d4e0ec"

# Ink (text)
INK = "#2a3b4a"
INK_2 = "#607182"
INK_3 = "#92a2b4"

# Accent (rare)
PEACH = "#ffd4c2"
MINT = "#c8eedd"
LEMON = "#fef0bc"
LILAC = "#e4d4f5"

# Semantic
DANGER_BG = "#ffe5e0"
DANGER_FG = "#c44a3d"

# ---------- Radius ----------
R_SM = 8      # 작은 버튼, input
R_MD = 14     # 카드 내부 요소
R_LG = 20     # 큰 카드
R_XL = 28     # 팝업 외곽
R_PILL = 999  # 완전 원형 pill

# ---------- Shadows ----------
# Qt 스타일시트는 box-shadow를 직접 지원하지 않으므로 QGraphicsDropShadowEffect로 표현.
# (blur_radius, offset_x, offset_y, color_rgba)
SHADOW_SM = (12, 0, 2, (90, 140, 180, int(0.08 * 255)))
SHADOW_MD = (20, 0, 6, (90, 140, 180, int(0.12 * 255)))
SHADOW_LG = (36, 0, 14, (90, 140, 180, int(0.18 * 255)))
SHADOW_PRIMARY = (10, 0, 4, (74, 149, 208, int(0.35 * 255)))
SHADOW_TODAY_BAR = (6, 0, 2, (39, 102, 158, int(0.25 * 255)))

# ---------- Spacing (8px base) ----------
SP_XS = 4
SP_SM = 8
SP = 12
SP_MD = 14
SP_LG = 16
SP_XL = 20
SP_2XL = 24
SP_3XL = 28
SP_4XL = 36

# ---------- Typography ----------
# Qt는 comma-separated font family를 자동 fallback해 준다.
FONT_UI = "Gowun Dodum, Malgun Gothic, sans-serif"
FONT_FUN = "Gaegu, Gowun Dodum, Malgun Gothic, sans-serif"
FONT_MONO = "Nanum Gothic Coding, Consolas, monospace"

# ---------- Window sizes ----------
SETTINGS_W = 860
SETTINGS_H = 600
POPUP_W = 440
POPUP_H = 220
TITLEBAR_H = 36
SIDEBAR_W = 200
POPUP_MARGIN = 24     # 화면 가장자리 여백
POPUP_CHAR_PANEL_W = 150
POPUP_CHAR_SIZE = 130
POPUP_DROPLET_SIZE = 72   # 설정창 캐릭터 그리드용


def qcolor_rgba(rgba: tuple) -> str:
    r, g, b, a = rgba
    return f"rgba({r}, {g}, {b}, {a})"
