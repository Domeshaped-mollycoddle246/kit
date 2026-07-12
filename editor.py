"""캡처 이미지 편집창 (Qt/PySide6).

사용법: python editor.py <이미지경로>
도구: 모자이크 / 박스 / 화살표 / 펜 / 글자 / 색상 / 실행취소 / 복사 / 저장

* 화면에는 축소해서 보여주지만, 편집·저장은 항상 '원본 해상도'로 합니다.
  (레티나 캡처도 화질 손실 없음)
"""

import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QInputDialog, QLabel,
                               QPushButton, QVBoxLayout, QWidget)

FONT_CANDIDATES = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
]
MAX_W, MAX_H = 1400, 860
COLORS = [("빨강", (255, 59, 48)), ("노랑", (255, 204, 0)), ("초록", (52, 199, 89)),
          ("파랑", (0, 122, 255)), ("검정", (0, 0, 0)), ("흰색", (255, 255, 255))]


def load_font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def pil_to_pixmap(img: Image.Image) -> QPixmap:
    rgba = img.convert("RGBA")
    data = rgba.tobytes("raw", "RGBA")
    qimg = QImage(data, rgba.width, rgba.height, QImage.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimg)


class Canvas(QWidget):
    """축소본을 보여주고 마우스 입력을 받는 영역 (실제 편집은 원본에)."""

    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self.setFixedSize(*editor.disp_size)
        self.setCursor(Qt.CrossCursor)
        self.pixmap = None
        self.rebuild()
        self.start = None
        self.cur = None
        self.pen_points = []      # 화면 좌표 (미리보기용)
        self.dragging = False

    def rebuild(self):
        dw, dh = self.editor.disp_size
        disp = self.editor.work.resize((dw, dh), Image.BILINEAR) \
            if (dw, dh) != self.editor.work.size else self.editor.work
        self.pixmap = pil_to_pixmap(disp)
        self.update()

    def _clamp(self, e):
        dw, dh = self.editor.disp_size
        x = min(max(int(e.position().x()), 0), dw - 1)
        y = min(max(int(e.position().y()), 0), dh - 1)
        return x, y

    # ---- 화면 그리기 (드래그 중 미리보기) ----
    def paintEvent(self, event):
        p = QPainter(self)
        if self.pixmap:
            p.drawPixmap(0, 0, self.pixmap)
        if self.dragging and self.start and self.cur:
            tool = self.editor.tool
            pen = QPen(QColor(*self.editor.color))
            pen.setWidth(3)
            if tool == "crop":
                pen = QPen(QColor(80, 80, 80))
                pen.setWidth(2)
                pen.setStyle(Qt.DashLine)
            p.setPen(pen)
            x0, y0 = self.start
            x1, y1 = self.cur
            if tool in ("mosaic", "rect", "crop"):
                p.drawRect(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
            elif tool == "arrow":
                p.drawLine(x0, y0, x1, y1)
            elif tool == "pen" and len(self.pen_points) > 1:
                for a, b in zip(self.pen_points, self.pen_points[1:]):
                    p.drawLine(a[0], a[1], b[0], b[1])
        p.end()

    # ---- 마우스 ----
    def mousePressEvent(self, e):
        x, y = self._clamp(e)
        if self.editor.tool == "text":
            self.editor.add_text(x, y)
            return
        self.start = (x, y)
        self.cur = (x, y)
        self.pen_points = [(x, y)]
        self.dragging = True

    def mouseMoveEvent(self, e):
        if not self.dragging:
            return
        self.cur = self._clamp(e)
        self.pen_points.append(self.cur)
        self.update()

    def mouseReleaseEvent(self, e):
        if not self.dragging:
            return
        self.dragging = False
        self.editor.apply_edit(self.editor.tool, self.start, self._clamp(e),
                               list(self.pen_points))
        self.start = self.cur = None
        self.pen_points = []
        self.rebuild()


class Editor(QWidget):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.work = Image.open(path).convert("RGB")   # 항상 원본 해상도 유지

        # 화면 표시 배율 (편집엔 영향 없음)
        self.scale = min(1.0, MAX_W / self.work.width, MAX_H / self.work.height)
        self.disp_size = (max(1, int(self.work.width * self.scale)),
                          max(1, int(self.work.height * self.scale)))

        self.undo_stack = []
        self.tool = "mosaic"
        self.color = (255, 59, 48)

        self.setWindowTitle("캡처 편집 — " + os.path.basename(path))
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        # ---- 도구 막대 ----
        bar = QHBoxLayout()
        self.tool_btns = {}
        for key, label in [("mosaic", "모자이크"), ("rect", "박스"),
                           ("arrow", "화살표"), ("pen", "펜"),
                           ("text", "글자"), ("crop", "자르기")]:
            b = QPushButton(label)
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, k=key: self.set_tool(k))
            bar.addWidget(b)
            self.tool_btns[key] = b
        self.tool_btns["mosaic"].setChecked(True)

        bar.addWidget(QLabel("  색:"))
        self.color_btns = []
        for name, rgb in COLORS:
            b = QPushButton()
            b.setFixedSize(26, 26)
            b.setToolTip(name)
            b.clicked.connect(lambda _=False, c=rgb: self.set_color(c))
            self.color_btns.append((b, rgb))
            bar.addWidget(b)
        self._refresh_colors()

        bar.addSpacing(10)
        for label, fn in [("↩︎ 실행취소", self.undo), ("복사", self.copy),
                          ("저장", self.save)]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            bar.addWidget(b)
        bar.addStretch()
        root.addLayout(bar)

        self.canvas = Canvas(self)
        root.addWidget(self.canvas)

        self.hint = QLabel("드래그해서 그리세요 · 저장하면 원본 화질 그대로 저장돼요")
        self.hint.setStyleSheet("color: gray; font-size: 12px;")
        root.addWidget(self.hint)

    # ---- 도구/색 선택 표시 ----
    def set_tool(self, key):
        self.tool = key
        for k, b in self.tool_btns.items():
            b.setChecked(k == key)

    def set_color(self, rgb):
        self.color = rgb
        self._refresh_colors()

    def _refresh_colors(self):
        for b, rgb in self.color_btns:
            border = "3px solid #333" if rgb == self.color else "1px solid #aaa"
            b.setStyleSheet(f"background-color: rgb{rgb}; border: {border}; border-radius: 5px;")

    # ---- 좌표/크기 변환 (화면 → 원본) ----
    def to_img(self, pt):
        x = min(max(int(pt[0] / self.scale), 0), self.work.width - 1)
        y = min(max(int(pt[1] / self.scale), 0), self.work.height - 1)
        return x, y

    def px(self, n):
        """화면에서 n픽셀 굵기로 보이도록 원본 기준 굵기를 계산."""
        return max(n, int(round(n / self.scale)))

    # ---- 편집 적용 (원본 이미지에) ----
    def push_undo(self):
        self.undo_stack.append(self.work.copy())
        if len(self.undo_stack) > 10:
            self.undo_stack.pop(0)

    def undo(self):
        if self.undo_stack:
            self.work = self.undo_stack.pop()
            self.recalc()   # 자르기 취소 시 창 크기도 되돌아가도록

    def recalc(self):
        """이미지 크기가 바뀌었을 때(자르기 등) 화면 배율·창 크기를 다시 계산."""
        self.scale = min(1.0, MAX_W / self.work.width, MAX_H / self.work.height)
        self.disp_size = (max(1, int(self.work.width * self.scale)),
                          max(1, int(self.work.height * self.scale)))
        self.canvas.setFixedSize(*self.disp_size)
        self.canvas.rebuild()
        self.adjustSize()

    def apply_edit(self, tool, p0, p1, points):
        (x0, y0), (x1, y1) = self.to_img(p0), self.to_img(p1)
        if tool in ("mosaic", "rect", "crop") and abs(x1 - x0) < 3 and abs(y1 - y0) < 3:
            return
        self.push_undo()
        if tool == "crop":
            box = (min(x0, x1), min(y0, y1), max(x0, x1) + 1, max(y0, y1) + 1)
            self.work = self.work.crop(box)
            self.recalc()
            return
        draw = ImageDraw.Draw(self.work)
        if tool == "mosaic":
            self._mosaic(x0, y0, x1, y1)
        elif tool == "rect":
            box = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
            draw.rectangle(box, outline=self.color, width=self.px(3))
        elif tool == "arrow":
            self._arrow(draw, (x0, y0), (x1, y1))
        elif tool == "pen" and len(points) > 1:
            img_pts = [self.to_img(p) for p in points]
            draw.line(img_pts, fill=self.color, width=self.px(3), joint="curve")

    def _mosaic(self, x0, y0, x1, y1):
        box = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        region = self.work.crop(box)
        if region.width < 2 or region.height < 2:
            return
        pixel = self.px(12)
        small = region.resize((max(1, region.width // pixel),
                               max(1, region.height // pixel)))
        self.work.paste(small.resize(region.size, Image.NEAREST), box)

    def _arrow(self, draw, p0, p1):
        w = self.px(4)
        head = self.px(18)
        draw.line([p0, p1], fill=self.color, width=w)
        angle = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
        for a in (angle - math.radians(28), angle + math.radians(28)):
            x = p1[0] - head * math.cos(a)
            y = p1[1] - head * math.sin(a)
            draw.line([p1, (x, y)], fill=self.color, width=w)

    def add_text(self, x, y):
        txt, ok = QInputDialog.getText(self, "글자 넣기", "표시할 글자를 입력하세요:")
        if ok and txt:
            self.push_undo()
            ix, iy = self.to_img((x, y))
            ImageDraw.Draw(self.work).text((ix, iy), txt, fill=self.color,
                                           font=load_font(self.px(28)))
            self.canvas.rebuild()

    # ---- 내보내기 (원본 해상도) ----
    def save(self):
        stem, _ = os.path.splitext(self.path)
        out = stem + "_편집.png"
        self.work.save(out)
        self.setWindowTitle("저장됨 ✓ — " + os.path.basename(out))
        subprocess.run(["open", "-R", out])

    def copy(self):
        QApplication.clipboard().setPixmap(pil_to_pixmap(self.work))
        self.setWindowTitle("클립보드에 복사됨 ✓ (Cmd+V 로 붙여넣기)")


def main():
    if len(sys.argv) < 2:
        print("사용법: python editor.py <이미지경로>")
        return
    app = QApplication(sys.argv)
    win = Editor(sys.argv[1])
    win.show()
    win.raise_()
    win.activateWindow()
    app.exec()


if __name__ == "__main__":
    main()
