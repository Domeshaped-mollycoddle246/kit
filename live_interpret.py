"""실시간(거의) 통역 창.

동작 방식:
- 마이크를 2초 조각으로 잘게 들으면서 버퍼에 모으고,
- 말이 잠깐 멈추면(조용해지면) 그때까지 모은 소리를 한 번에 인식합니다.
  → 단어가 중간에서 잘리지 않아 훨씬 정확해요.
- 직전 문장을 힌트로 넘겨 문맥도 이어집니다.

* rumps(메뉴바 앱)와 충돌하지 않도록 '별도 프로그램'으로 실행됩니다.
"""

import audioop
import glob
import os
import shutil
import subprocess
import sys
import time
import wave
from datetime import datetime

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QLabel,
                               QPushButton, QTextEdit, QVBoxLayout, QWidget)

from features import avdevices, config, transcribe, translate

LANG_OPTIONS = [("한국어", "ko"), ("English", "en"), ("日本語", "ja"), ("中文", "zh")]
TMPDIR = "/tmp/biseo_live"

SEGMENT_SEC = 2        # 잘게 듣는 단위 (짧을수록 반응 빠름)
MAX_BUFFER_SEC = 10    # 말이 계속 이어져도 최대 이 길이마다 한 번 인식
QUIET_RMS = 400        # 이보다 조용하면 '말이 멈춤'으로 판단


def _tail_rms(path: str, tail_sec: float = 0.5) -> int:
    """조각 끝부분의 소리 크기 (말이 멈췄는지 판단용)."""
    try:
        with wave.open(path) as w:
            rate, n = w.getframerate(), w.getnframes()
            take = min(n, int(rate * tail_sec))
            if take <= 0:
                return 0
            w.setpos(n - take)
            return audioop.rms(w.readframes(take), 2)
    except Exception:
        return QUIET_RMS + 1   # 판단 불가 시 '말하는 중'으로 취급


def _max_rms(path: str) -> int:
    try:
        with wave.open(path) as w:
            frames = w.readframes(w.getnframes())
            return audioop.rms(frames, 2) if frames else 0
    except Exception:
        return 0


def _concat_wavs(paths, out_path):
    """같은 형식의 wav 조각들을 하나로 이어 붙입니다."""
    with wave.open(paths[0]) as first:
        params = first.getparams()
    with wave.open(out_path, "wb") as out:
        out.setparams(params)
        for p in paths:
            with wave.open(p) as w:
                out.writeframes(w.readframes(w.getnframes()))


class Worker(QThread):
    result = Signal(str, str)   # (원문, 번역)
    status = Signal(str)

    def __init__(self, win):
        super().__init__()
        self.win = win
        self._running = True
        self.proc = None
        self.prev_text = ""     # 직전 인식 결과 (문맥 힌트)

    def _resolve_mic(self):
        """장치 '이름'으로 최신 번호를 다시 찾습니다.
        (이어폰을 꽂거나 빼면 번호가 바뀌기 때문)"""
        want = self.win.mic_name()
        try:
            _, devs = avdevices.list_devices()
        except Exception:
            return None
        for idx, name in devs.items():
            if name == want:
                return idx
        return avdevices.find_mic(devs)   # 못 찾으면 기본 마이크로

    def run(self):
        shutil.rmtree(TMPDIR, ignore_errors=True)
        os.makedirs(TMPDIR, exist_ok=True)

        mic = self._resolve_mic()
        if mic is None:
            self.status.emit("⚠️ 마이크를 찾지 못했어요. 마이크 연결을 확인해 주세요.")
            return

        cmd = [avdevices.FFMPEG, "-hide_banner", "-y",
               "-f", "avfoundation", "-i", f":{mic}",
               "-ac", "1", "-ar", "16000",
               "-f", "segment", "-segment_time", str(SEGMENT_SEC),
               "-reset_timestamps", "1",
               os.path.join(TMPDIR, "seg_%04d.wav")]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
        self.status.emit("🎧 듣는 중… 말씀하세요 (말을 잠깐 멈추면 자막이 떠요)")

        buffer = []          # 아직 인식 안 한 조각들
        buffer_sec = 0
        processed = set()

        while self._running:
            # 마이크가 안 열리면(장치 바뀜 등) ffmpeg가 바로 죽어요 → 알려주기
            if self.proc.poll() is not None:
                self.status.emit("⚠️ 마이크 연결에 실패했어요. 🎙 목록에서 마이크를 "
                                 "다시 선택하거나 창을 닫았다 열어주세요.")
                return
            files = sorted(glob.glob(os.path.join(TMPDIR, "seg_*.wav")))
            for f in files[:-1]:          # 마지막 파일은 아직 녹음 중
                if f in processed:
                    continue
                processed.add(f)
                buffer.append(f)
                buffer_sec += SEGMENT_SEC

                # 말이 멈췄거나(조각 끝이 조용) 버퍼가 가득 → 한 번에 인식
                if _tail_rms(f) < QUIET_RMS or buffer_sec >= MAX_BUFFER_SEC:
                    self._flush(buffer)
                    buffer, buffer_sec = [], 0
            time.sleep(0.3)

        # 중지 → 녹음 종료 후 남은 조각 마저 처리
        if self.proc:
            try:
                self.proc.communicate(input=b"q", timeout=5)
            except Exception:
                self.proc.terminate()
        leftovers = [f for f in sorted(glob.glob(os.path.join(TMPDIR, "seg_*.wav")))
                     if f not in processed]
        self._flush(buffer + leftovers)

    def _flush(self, chunk_files):
        chunk_files = [f for f in chunk_files if os.path.exists(f)]
        if not chunk_files:
            return
        try:
            # 전부 조용한 조각이면 인식할 필요 없음
            if max(_max_rms(f) for f in chunk_files) < QUIET_RMS:
                return
            merged = os.path.join(TMPDIR, "merged.wav")
            _concat_wavs(chunk_files, merged)
            src, tgt = self.win.src_code(), self.win.tgt_code()
            text = transcribe.transcribe_live(merged, src, self.prev_text)
            if text.strip():
                self.prev_text = (self.prev_text + " " + text)[-300:]
                tr = translate.translate(text, src, tgt) if src != tgt else text
                self.result.emit(text, tr)
        except Exception as e:
            self.status.emit("처리 오류: " + str(e))
        finally:
            for f in chunk_files:
                try:
                    os.remove(f)
                except Exception:
                    pass

    def stop(self):
        self._running = False


class LiveWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("실시간 통역")
        self.resize(600, 500)
        layout = QVBoxLayout(self)

        # 1줄: 언어 선택 + 시작/중지/저장
        top = QHBoxLayout()
        top.addWidget(QLabel("말하는 언어"))
        self.src_combo = QComboBox()
        self.tgt_combo = QComboBox()
        for name, code in LANG_OPTIONS:
            self.src_combo.addItem(name, code)
            self.tgt_combo.addItem(name, code)
        self.src_combo.setCurrentText("한국어")
        self.tgt_combo.setCurrentText("English")
        top.addWidget(self.src_combo)
        top.addWidget(QLabel("→ 번역"))
        top.addWidget(self.tgt_combo)
        top.addStretch()
        self.toggle_btn = QPushButton("⏹ 중지")
        self.toggle_btn.clicked.connect(self.toggle)
        top.addWidget(self.toggle_btn)
        self.save_btn = QPushButton("💾 저장")
        self.save_btn.clicked.connect(self.save)
        top.addWidget(self.save_btn)
        layout.addLayout(top)

        # 2줄: 마이크 선택 + 글자 크기 + 지우기
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("🎙"))
        self.mic_combo = QComboBox()
        try:
            _, audio_devs = avdevices.list_devices()
        except Exception:
            audio_devs = {}
        default_mic = avdevices.find_mic(audio_devs) if audio_devs else None
        for idx in sorted(audio_devs):
            self.mic_combo.addItem(audio_devs[idx], idx)
            if idx == default_mic:
                self.mic_combo.setCurrentIndex(self.mic_combo.count() - 1)
        self.mic_combo.currentIndexChanged.connect(self._mic_changed)
        row2.addWidget(self.mic_combo)
        row2.addStretch()
        for label, delta in [("A−", -2), ("A+", +2)]:
            b = QPushButton(label)
            b.setFixedWidth(44)
            b.clicked.connect(lambda _=False, d=delta: self.change_font(d))
            row2.addWidget(b)
        clear_btn = QPushButton("🗑 지우기")
        clear_btn.clicked.connect(lambda: self.view.clear())
        row2.addWidget(clear_btn)
        layout.addLayout(row2)

        self.status_lbl = QLabel("준비 중…")
        layout.addWidget(self.status_lbl)

        self.font_px = 15
        self.view = QTextEdit()
        self.view.setReadOnly(True)
        self.view.setStyleSheet(f"font-size: {self.font_px}px;")
        layout.addWidget(self.view)

        self.worker = None
        self.start()

    # ---- 설정값 읽기 ----
    def src_code(self):
        return self.src_combo.currentData()

    def tgt_code(self):
        return self.tgt_combo.currentData()

    def mic_index(self):
        return self.mic_combo.currentData()

    def mic_name(self):
        return self.mic_combo.currentText()

    def change_font(self, delta):
        self.font_px = min(max(self.font_px + delta, 11), 33)
        self.view.setStyleSheet(f"font-size: {self.font_px}px;")

    def _mic_changed(self, _):
        # 마이크를 바꾸면 듣기를 다시 시작해 새 마이크를 사용
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(4000)
            self.start()

    # ---- 시작/중지 ----
    def start(self):
        self.worker = Worker(self)
        self.worker.result.connect(self.on_result)
        self.worker.status.connect(self.status_lbl.setText)
        self.worker.start()
        self.toggle_btn.setText("⏹ 중지")

    def toggle(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(6000)
            self.status_lbl.setText("⏸ 중지됨. '▶ 시작'을 누르면 다시 들어요.")
            self.toggle_btn.setText("▶ 시작")
        else:
            self.start()

    def on_result(self, original, translated):
        self.view.append(f"🗣 {original}\n→ {translated}\n")
        bar = self.view.verticalScrollBar()
        bar.setValue(bar.maximum())

    def save(self):
        content = self.view.toPlainText().strip()
        if not content:
            return
        out = config.save_dir() / datetime.now().strftime("통역_%Y%m%d_%H%M%S.txt")
        out.write_text(content, encoding="utf-8")
        self.status_lbl.setText(f"저장됨: {out.name}")
        subprocess.run(["open", "-R", str(out)])

    def closeEvent(self, e):
        if self.worker:
            self.worker.stop()
            self.worker.wait(6000)
        e.accept()


def main():
    app = QApplication(sys.argv)
    win = LiveWindow()
    win.show()
    win.raise_()
    win.activateWindow()
    app.exec()


if __name__ == "__main__":
    main()
