#!/usr/bin/env python3
"""플로팅 토끼 — 작게 떠 있는 비서 팔레트.

평소엔 움직이는 토끼만 조그맣게 떠 있고,
토끼를 클릭하면 메뉴가 열립니다. 드래그하면 자리를 옮길 수 있어요.
"""

import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

from PySide6.QtCore import (Qt, QEasingCurve, QPoint, QPropertyAnimation,
                            QSequentialAnimationGroup, QSize, QTimer)
from PySide6.QtGui import QAction, QMovie
from PySide6.QtWidgets import (QApplication, QFileDialog, QInputDialog,
                               QLabel, QMenu, QMessageBox, QWidget)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

RABBIT_GIF = os.path.join(APP_DIR, "assets", "rabbit_animated.webp")
RABBIT_SIZE = 88    # 토끼 표시 크기(px)
JUMP_HEIGHT = 28    # 점프 높이(px)
CLICK_SLOP = 6      # 이 거리(px) 이상 움직이면 클릭이 아니라 드래그

WEB_TOOLS = [
    ("모든 변환(all-to-all)", "https://commme.github.io/all-to-all/"),
    ("파일 → PNG 변환", "https://commme.github.io/file-to-png/"),
    ("압축 풀기", "https://commme.github.io/unzip-tool/"),
    ("이미지 도구", "https://commme.github.io/image-tools/"),
    ("AI 도구 모음", "https://commme.github.io/ai-tools-hub/"),
]


def _fmt(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


class RabbitPalette(QWidget):
    """토끼 한 마리 + 클릭하면 열리는 메뉴."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("비서")
        self.setWindowFlags(Qt.WindowType.Window
                            | Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(RABBIT_SIZE + 20, RABBIT_SIZE + JUMP_HEIGHT + 26)

        # ----- 상태 -----
        self._rec_start = None      # 화면 녹화 시작 시각
        self._aud_start = None      # 마이크 시작 시각
        self._mic_purpose = None    # "record" | "interpret"
        self._busy = None           # 백그라운드 작업 설명 (없으면 None)
        self._pending = None        # 백그라운드 → 메인 스레드 전달용
        self._drag_start = None
        self._drag_window_pos = None

        # ----- UI: 토끼 + 상태 글자 -----
        self.rabbit = QLabel(self)
        self.rabbit.setFixedSize(RABBIT_SIZE, RABBIT_SIZE)
        self.rabbit.move(10, JUMP_HEIGHT)
        if os.path.exists(RABBIT_GIF):
            self.movie = QMovie(RABBIT_GIF)
            self.movie.setScaledSize(QSize(RABBIT_SIZE, RABBIT_SIZE))
            self.rabbit.setMovie(self.movie)
            self.movie.start()
        else:
            self.rabbit.setText("🐰")
            self.rabbit.setStyleSheet("font-size: 64px;")
            self.rabbit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 마우스는 창에서 한꺼번에 처리 (클릭=메뉴, 드래그=이동)
        self.rabbit.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.status = QLabel("", self)
        self.status.setGeometry(0, self.height() - 22, self.width(), 20)
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet(
            "color: #c0392b; font-size: 11px; font-weight: 600;"
            "background: rgba(255,255,255,190); border-radius: 9px;")
        self.status.hide()

        self._jump_anim = None
        self._load_position()

        # 상태 갱신 + 백그라운드 결과 처리 (1초마다)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

        # 가끔 혼자 폴짝
        self._idle_jump = QTimer(self)
        self._idle_jump.timeout.connect(self._jump)
        self._idle_jump.start(4000)

    # ============ 점프 ============
    def _jump(self):
        if self._jump_anim and \
           self._jump_anim.state() == QSequentialAnimationGroup.State.Running:
            return
        ground = QPoint(10, JUMP_HEIGHT)
        top = QPoint(10, 2)

        up = QPropertyAnimation(self.rabbit, b"pos")
        up.setDuration(240)
        up.setStartValue(ground)
        up.setEndValue(top)
        up.setEasingCurve(QEasingCurve.Type.OutQuad)

        down = QPropertyAnimation(self.rabbit, b"pos")
        down.setDuration(400)
        down.setStartValue(top)
        down.setEndValue(ground)
        down.setEasingCurve(QEasingCurve.Type.OutBounce)

        g = QSequentialAnimationGroup(self)
        g.addAnimation(up)
        g.addAnimation(down)
        g.start()
        self._jump_anim = g

    # ============ 마우스: 클릭=메뉴, 드래그=이동 ============
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_start = e.globalPosition().toPoint()
            self._drag_window_pos = self.pos()

    def mouseMoveEvent(self, e):
        if self._drag_start is not None:
            delta = e.globalPosition().toPoint() - self._drag_start
            self.move(self._drag_window_pos + delta)

    def mouseReleaseEvent(self, e):
        if self._drag_start is None:
            return
        moved = (e.globalPosition().toPoint() - self._drag_start).manhattanLength()
        self._drag_start = None
        self._save_position()
        if moved < CLICK_SLOP:          # 드래그가 아니라 클릭
            self._jump()
            self._show_menu()

    # ============ 메뉴 ============
    def _show_menu(self):
        m = QMenu(self)

        cap = m.addMenu("⌗ 캡처")
        cap.addAction("영역 캡처", lambda: self._in_thread(self._cap_area))
        cap.addAction("전체화면 캡처", lambda: self._in_thread(self._cap_full))
        cap.addAction("창 캡처", lambda: self._in_thread(self._cap_window))
        cap.addAction("캡처 후 편집(모자이크/표시)",
                      lambda: self._in_thread(self._cap_edit))
        cap.addAction("캡처 폴더 열기", self._open_folder)

        from features import audio, record
        rec_label = "⏹︎ 화면 녹화 중지" if record.is_recording() else "⏺︎ 화면 녹화 시작"
        m.addAction(rec_label, self._toggle_record)

        if audio.is_recording() and self._mic_purpose == "record":
            m.addAction("⏹︎ 음성 녹음 중지", self._toggle_audio)
        else:
            m.addAction("∿ 음성 녹음 시작", self._toggle_audio)

        m.addAction("✎ 녹음을 글자로 변환…", self._transcribe_file)

        m.addSeparator()
        if audio.is_recording() and self._mic_purpose == "interpret":
            m.addAction("⏹︎ 통역 중지", self._toggle_interpret)
        else:
            m.addAction("▶︎ 통역 시작 (말→번역)", self._toggle_interpret)
        m.addAction("실시간 통역 창", self._open_live)

        tr = m.addMenu("⇄ 번역 (글)")
        from features import translate as tr_mod
        for code in ("en", "ko", "ja", "zh"):
            tr.addAction(f"→ {tr_mod.LANGS[code]}",
                         lambda c=code: self._translate_text(c))

        web = m.addMenu("✦ 웹 도구")
        for label, url in WEB_TOOLS:
            web.addAction(label, lambda u=url: webbrowser.open(u))

        m.addSeparator()
        m.addAction("⌂ 바탕화면 청소", self._cleanup)

        st = m.addMenu("⚙︎ 설정")
        from features import autostart
        auto = QAction("로그인 시 자동 시작", st)
        auto.setCheckable(True)
        auto.setChecked(autostart.is_enabled())
        auto.triggered.connect(self._toggle_autostart)
        st.addAction(auto)
        st.addAction("저장 폴더 변경…", self._change_folder)

        m.addSeparator()
        m.addAction("✕ 토끼 숨기기 (종료)", self.close)

        # 토끼 아래에 메뉴 표시
        m.exec(self.mapToGlobal(QPoint(0, self.height())))

    # ============ 캡처 ============
    def _cap_area(self):
        from features import capture
        capture.capture_area()

    def _cap_full(self):
        from features import capture
        capture.capture_full()

    def _cap_window(self):
        from features import capture
        capture.capture_window()

    def _cap_edit(self):
        from features import capture
        path = capture.capture_area_for_edit()
        if path:
            subprocess.Popen([sys.executable,
                              os.path.join(APP_DIR, "editor.py"), path])

    def _open_folder(self):
        from features import capture
        capture.open_folder()

    # ============ 화면 녹화 ============
    def _toggle_record(self):
        from features import record
        if record.is_recording():
            self._busy = "저장중…"
            self._in_thread(self._stop_record)
        else:
            try:
                record.start()
                self._rec_start = time.time()
            except Exception as e:
                self._alert("녹화 오류", str(e))

    def _stop_record(self):
        from features import record
        out = record.stop()
        self._rec_start = None
        self._pending = ("rec_saved", out)

    # ============ 음성 녹음 ============
    def _toggle_audio(self):
        from features import audio
        if audio.is_recording():
            if self._mic_purpose != "record":
                self._alert("잠깐만요", "지금 통역 녹음 중이에요. 통역을 먼저 멈춰주세요.")
                return
            self._busy = "저장중…"
            self._in_thread(self._stop_audio)
        else:
            self._start_mic("record")

    def _stop_audio(self):
        from features import audio
        out = audio.stop()
        self._mic_purpose = None
        self._aud_start = None
        self._pending = ("aud_saved", out)

    def _start_mic(self, purpose) -> bool:
        from features import audio
        try:
            audio.start()
            self._mic_purpose = purpose
            self._aud_start = time.time()
            return True
        except Exception as e:
            self._alert("마이크 오류", str(e))
            return False

    # ============ 통역 ============
    def _toggle_interpret(self):
        from features import audio
        if audio.is_recording():
            if self._mic_purpose != "interpret":
                self._alert("잠깐만요", "지금 음성 녹음 중이에요. 녹음을 먼저 멈춰주세요.")
                return
            self._busy = "통역중…"
            self._in_thread(self._stop_interpret)
        else:
            self._start_mic("interpret")

    def _stop_interpret(self):
        from features import audio, transcribe, translate
        out = audio.stop()
        self._mic_purpose = None
        self._aud_start = None
        if not out:
            self._pending = ("error", "녹음이 저장되지 않았어요. 마이크 권한을 확인해 주세요.")
            return
        try:
            text = transcribe.transcribe_plain(out, "ko")
            translated = translate.translate(text, "ko", "en") if text else ""
            res = str(Path(out).with_suffix("")) + "_통역.txt"
            Path(res).write_text(
                f"[원문 한국어]\n{text}\n\n[번역 English]\n{translated}\n",
                encoding="utf-8")
            self._pending = ("done_file", res)
        except Exception as e:
            self._pending = ("error", str(e))

    def _open_live(self):
        subprocess.Popen([sys.executable,
                          os.path.join(APP_DIR, "live_interpret.py")])

    # ============ 글자 변환 ============
    def _transcribe_file(self):
        if self._busy:
            self._alert("잠깐만요", "이미 처리 중이에요. 끝나면 알려드릴게요.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "글자로 변환할 녹음 파일을 고르세요", str(Path.home()),
            "오디오 파일 (*.m4a *.mp3 *.wav *.mp4 *.aac *.flac);;모든 파일 (*)")
        if not path:
            return
        self._busy = "변환중…"
        self._in_thread(self._do_transcribe, path)

    def _do_transcribe(self, path):
        from features import transcribe
        try:
            self._pending = ("done_file", transcribe.transcribe_to_file(path))
        except Exception as e:
            self._pending = ("error", str(e))

    # ============ 번역 (글) ============
    def _translate_text(self, tgt):
        from features import translate
        text, ok = QInputDialog.getMultiLineText(
            self, "번역",
            f"{translate.LANGS[tgt]}(으)로 번역할 글을 입력/붙여넣으세요.\n(출발 언어는 자동 판별)")
        if not (ok and text.strip()):
            return
        try:
            direction, result = translate.translate_to(text.strip(), tgt)
            box = QMessageBox(self)
            box.setWindowTitle(f"번역 결과 ({direction})")
            box.setText(result)
            box.setStandardButtons(QMessageBox.StandardButton.Ok)
            box.exec()
        except Exception as e:
            self._alert("번역 오류", str(e))

    # ============ 청소 / 설정 ============
    def _cleanup(self):
        resp = QMessageBox.question(
            self, "바탕화면 청소",
            "바탕화면 파일들을 종류별로 '정리됨_날짜' 폴더에 정리할까요?\n"
            "(삭제하지 않고 옮기기만 합니다)")
        if resp != QMessageBox.StandardButton.Yes:
            return
        from features import cleanup
        moved, folders = cleanup.clean_desktop()
        self._alert("정리 완료",
                    f"파일 {moved}개를 정리했어요.\n폴더 {folders}개는 그대로 두었습니다.")

    def _toggle_autostart(self):
        from features import autostart
        try:
            if autostart.is_enabled():
                autostart.disable()
                self._alert("자동 시작 끔", "다음 로그인부터 자동으로 켜지지 않아요.")
            else:
                autostart.enable()
                self._alert("자동 시작 켬 ✅", "다음부터 로그인하면 자동으로 켜져요.")
        except Exception as e:
            self._alert("설정 오류", str(e))

    def _change_folder(self):
        from features import config
        path = QFileDialog.getExistingDirectory(
            self, "캡처·녹화·녹음을 저장할 폴더를 고르세요", config.get("save_dir"))
        if path:
            config.set("save_dir", path)
            self._alert("저장 폴더 변경됨 📂", f"이제 여기에 저장돼요:\n{path}")

    # ============ 공통 ============
    def _in_thread(self, fn, *args):
        threading.Thread(target=fn, args=args, daemon=True).start()

    def _alert(self, title, message):
        QMessageBox.information(self, title, message)

    def _tick(self):
        # 백그라운드 작업 결과 처리 (메인 스레드에서)
        if self._pending:
            kind, payload = self._pending
            self._pending = None
            self._busy = None
            if kind == "rec_saved":
                self._file_saved_alert("화면 녹화 완료", payload,
                                       "화면 기록 권한이 없어서 화면을 못 담았어요.\n"
                                       "시스템 설정 → 개인정보 보호 및 보안 → "
                                       "화면 및 시스템 오디오 기록을 확인해 주세요.")
            elif kind == "aud_saved":
                self._audio_saved(payload)
            elif kind == "done_file":
                self._alert("완료 ✅", f"파일로 저장했어요:\n{os.path.basename(payload)}")
                subprocess.run(["open", payload])
            elif kind == "error":
                self._alert("오류", payload)

        # 상태 글자 갱신
        from features import audio, record
        parts = []
        if self._busy:
            parts.append("⋯ " + self._busy)
        if record.is_recording() and self._rec_start:
            parts.append("● 화면 " + _fmt(time.time() - self._rec_start))
        if audio.is_recording() and self._aud_start:
            label = "통역" if self._mic_purpose == "interpret" else "녹음"
            parts.append("● " + label + " " + _fmt(time.time() - self._aud_start))
        if parts:
            self.status.setText("  ".join(parts))
            self.status.show()
        else:
            self.status.hide()

    def _file_saved_alert(self, title, path, fail_msg):
        if path and os.path.exists(path) and os.path.getsize(path) > 0:
            self._alert(title, f"저장했어요:\n{os.path.basename(path)}")
            subprocess.run(["open", "-R", path])
        else:
            self._alert("저장되지 않았어요 ⚠️", fail_msg)

    def _audio_saved(self, out):
        if out and os.path.exists(out) and os.path.getsize(out) > 0:
            resp = QMessageBox.question(
                self, "음성 녹음 완료",
                f"저장됨: {os.path.basename(out)}\n\n이 녹음을 글자(텍스트)로 변환할까요?")
            if resp == QMessageBox.StandardButton.Yes:
                self._busy = "변환중…"
                self._in_thread(self._do_transcribe, out)
            else:
                subprocess.run(["open", "-R", out])
        else:
            self._alert("녹음이 저장되지 않았어요 ⚠️", "마이크 권한을 확인해 주세요.")

    # ============ 위치 저장/복원 ============
    def _save_position(self):
        try:
            from features import config
            config.set("palette_pos", {"x": self.pos().x(), "y": self.pos().y()})
        except Exception:
            pass

    def _load_position(self):
        try:
            from features import config
            pos = config.get("palette_pos")
        except Exception:
            pos = None
        if pos:
            self.move(pos.get("x", 100), pos.get("y", 100))
        else:
            geo = QApplication.primaryScreen().availableGeometry()
            self.move(geo.right() - self.width() - 24,
                      geo.bottom() - self.height() - 24)

    # ============ 종료 ============
    def closeEvent(self, event):
        # 녹화·녹음이 켜져 있으면 파일이 깨지지 않게 먼저 멈춥니다.
        try:
            from features import audio, record
            if record.is_recording():
                record.stop()
            if audio.is_recording():
                audio.stop()
        finally:
            event.accept()
            QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    w = RabbitPalette()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
