#!/usr/bin/env python3
"""플로팅 팔레트 윈도우 - 항상 위에 떠있는 메뉴 팔레트"""

import os
import sys
import subprocess
import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QTimer, QPoint, QRect
from PySide6.QtGui import QIcon, QPixmap, QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel, QScrollArea
)


class FloatingPaletteWindow(QMainWindow):
    """항상 위에 떠있는 메뉴 팔레트"""

    def __init__(self):
        super().__init__()
        self.animation_frame = 0
        self.is_hovering = False

        # 윈도우 스타일 설정
        self.setWindowTitle("🐰 비서 팔레트")
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )

        # 투명 배경
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 윈도우 크기 및 위치
        self.setFixedSize(340, 620)
        self._load_position()

        # UI 구성
        self._create_ui()

        # 애니메이션 타이머
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._animate_rabbit)
        self.animation_timer.start(100)

        # 마우스 추적
        self.setMouseTracking(True)

    def _create_ui(self):
        """UI 구성요소 생성"""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 토끼 아이콘 (헤더)
        header_layout = QHBoxLayout()

        self.rabbit_label = QLabel()
        self.rabbit_label.setStyleSheet("""
            QLabel {
                background-color: rgba(240, 240, 255, 200);
                border-radius: 15px;
                padding: 10px;
            }
        """)
        self._update_rabbit_icon()
        header_layout.addStretch()
        header_layout.addWidget(self.rabbit_label)
        header_layout.addStretch()

        # 타이틀
        title = QLabel("🐰 비서")
        title.setFont(QFont("System", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                color: #333;
                padding: 10px;
            }
        """)

        main_layout.addLayout(header_layout)
        main_layout.addWidget(title)

        # 스크롤 가능한 버튼 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: rgba(255, 255, 255, 200);
                border-radius: 10px;
            }
            QScrollBar:vertical {
                width: 8px;
                background-color: rgba(200, 200, 200, 100);
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(150, 150, 150, 150);
                border-radius: 4px;
            }
        """)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setSpacing(8)

        # 메뉴 버튼들
        menu_items = [
            ("📸 영역 캡처", self._run_capture_area),
            ("📸 전체 캡처", self._run_capture_full),
            ("📸 창 캡처", self._run_capture_window),
            ("✏️ 캡처 후 편집", self._run_capture_edit),
            ("📂 캡처 폴더 열기", self._run_open_folder),
            ("", None),  # 구분선
            ("🎥 화면 녹화", self._run_record),
            ("🎙️ 음성 녹음", self._run_audio),
            ("📝 글자 변환", self._run_transcribe),
            ("", None),
            ("🎤 통역 시작", self._run_interpret),
            ("💬 실시간 통역", self._run_live),
            ("🌍 번역하기", self._run_translate),
            ("", None),
            ("🌐 웹 도구", self._run_web_menu),
            ("🧹 청소", self._run_cleanup),
            ("⚙️ 설정", self._run_settings),
        ]

        for label, callback in menu_items:
            if not label:  # 구분선
                line = QLabel()
                line.setStyleSheet("""
                    QLabel {
                        border-bottom: 1px solid rgba(150, 150, 150, 100);
                        height: 0px;
                        margin: 5px 0px;
                    }
                """)
                scroll_layout.addWidget(line)
            else:
                btn = QPushButton(label)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(200, 230, 255, 200);
                        border: 1px solid rgba(150, 180, 220, 200);
                        border-radius: 8px;
                        padding: 10px;
                        color: #333;
                        font-weight: 500;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: rgba(150, 200, 255, 220);
                    }
                    QPushButton:pressed {
                        background-color: rgba(100, 180, 255, 220);
                    }
                """)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(callback)
                scroll_layout.addWidget(btn)

        scroll_layout.addStretch()
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        # 닫기 버튼
        close_btn = QPushButton("✕ 닫기")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 200, 200, 200);
                border: 1px solid rgba(255, 150, 150, 200);
                border-radius: 8px;
                padding: 8px;
                color: #333;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(255, 150, 150, 220);
            }
        """)
        close_btn.clicked.connect(self.close)
        main_layout.addWidget(close_btn)

        central.setLayout(main_layout)

    def _update_rabbit_icon(self):
        """토끼 아이콘 업데이트"""
        APP_DIR = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(APP_DIR, "assets", "rabbit_icon.png")

        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            scaled = pixmap.scaledToHeight(60, Qt.TransformationMode.SmoothTransformation)
            self.rabbit_label.setPixmap(scaled)
        else:
            self.rabbit_label.setText("🐰")

    def _animate_rabbit(self):
        """토끼 점프 애니메이션"""
        if self.is_hovering:
            APP_DIR = os.path.dirname(os.path.abspath(__file__))
            frame_path = os.path.join(
                APP_DIR, "assets", f"rabbit_jumping_{self.animation_frame % 8}.png"
            )

            if os.path.exists(frame_path):
                pixmap = QPixmap(frame_path)
                scaled = pixmap.scaledToHeight(60, Qt.TransformationMode.SmoothTransformation)
                self.rabbit_label.setPixmap(scaled)

            self.animation_frame += 1

    def mouseMoveEvent(self, event):
        """마우스 이동 시 토끼 애니메이션 시작"""
        if self.rabbit_label.geometry().contains(event.pos()):
            self.is_hovering = True
        else:
            self.is_hovering = False

    def _save_position(self):
        """윈도우 위치 저장"""
        try:
            from features import config
            config.set("palette_pos", {"x": self.pos().x(), "y": self.pos().y()})
        except:
            pass

    def _load_position(self):
        """저장된 윈도우 위치 로드"""
        try:
            from features import config
            pos = config.get("palette_pos")
            if pos:
                self.move(pos.get("x", 100), pos.get("y", 100))
            else:
                self._center_position()
        except:
            self._center_position()

    def _center_position(self):
        """윈도우를 화면 오른쪽에 배치"""
        screen = QApplication.primaryScreen()
        screen_geom = screen.availableGeometry()

        x = screen_geom.width() - self.width() - 20
        y = screen_geom.height() - self.height() - 20
        self.move(x, y)

    def moveEvent(self, event):
        """윈도우 이동 시 위치 저장"""
        super().moveEvent(event)
        self._save_position()

    # ===== 각 기능별 콜백 =====
    def _run_capture_area(self):
        from features import capture
        capture.capture_area()

    def _run_capture_full(self):
        from features import capture
        capture.capture_full()

    def _run_capture_window(self):
        from features import capture
        capture.capture_window()

    def _run_capture_edit(self):
        from features import capture
        path = capture.capture_area_for_edit()
        if path:
            APP_DIR = os.path.dirname(os.path.abspath(__file__))
            subprocess.Popen([sys.executable, os.path.join(APP_DIR, "editor.py"), path])

    def _run_open_folder(self):
        from features import capture
        capture.open_folder()

    def _run_record(self):
        from features import record
        if record.is_recording():
            record.stop()
        else:
            try:
                record.start()
            except Exception as e:
                print(f"Recording error: {e}")

    def _run_audio(self):
        from features import audio
        if audio.is_recording():
            audio.stop()
        else:
            try:
                audio.start()
            except Exception as e:
                print(f"Audio error: {e}")

    def _run_transcribe(self):
        from features import transcribe
        script = 'POSIX path of (choose file with prompt "글자로 변환할 녹음 파일을 고르세요")'
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        path = r.stdout.strip()
        if path and os.path.exists(path):
            try:
                transcribe.transcribe_to_file(path)
            except Exception as e:
                print(f"Transcribe error: {e}")

    def _run_interpret(self):
        from features import audio
        if audio.is_recording():
            audio.stop()
        else:
            try:
                audio.start()
            except Exception as e:
                print(f"Interpret error: {e}")

    def _run_live(self):
        APP_DIR = os.path.dirname(os.path.abspath(__file__))
        subprocess.Popen([sys.executable, os.path.join(APP_DIR, "live_interpret.py")])

    def _run_translate(self):
        try:
            from features import translate
            import rumps
            w = rumps.Window(
                message="번역할 글을 입력/붙여넣으세요.",
                title="번역",
                default_text="",
                ok="번역",
                cancel="취소",
                dimensions=(360, 140),
            )
            resp = w.run()
            if resp.clicked and resp.text.strip():
                direction, result = translate.translate_to(resp.text.strip(), "ko")
                rumps.alert(title=f"번역 결과 ({direction})", message=result)
        except Exception as e:
            print(f"Translate error: {e}")

    def _run_web_menu(self):
        WEB_TOOLS = [
            ("♻️ 모든 변환(all-to-all)", "https://commme.github.io/all-to-all/"),
            ("🔄 파일 → PNG 변환", "https://commme.github.io/file-to-png/"),
            ("🗜️ 압축 풀기", "https://commme.github.io/unzip-tool/"),
            ("🖼️ 이미지 도구", "https://commme.github.io/image-tools/"),
            ("🤖 AI 도구 모음", "https://commme.github.io/ai-tools-hub/"),
        ]
        for label, url in WEB_TOOLS:
            if label.startswith("♻️"):
                webbrowser.open(url)
                break

    def _run_cleanup(self):
        from features import cleanup
        moved, folders = cleanup.clean_desktop()
        print(f"Cleaned: {moved} files, {folders} folders")

    def _run_settings(self):
        print("Settings clicked - open via main menu")


def main():
    app = QApplication(sys.argv)
    window = FloatingPaletteWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
