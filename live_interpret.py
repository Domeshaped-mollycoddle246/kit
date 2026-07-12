"""실시간(거의) 통역 창.

동작 방식:
- 마이크를 2초 조각으로 잘게 들으면서 버퍼에 모으고,
- 말이 잠깐 멈추면(조용해지면) 그때까지 모은 소리를 한 번에 인식합니다.
  → 단어가 중간에서 잘리지 않아 훨씬 정확해요.
- 직전 문장을 힌트로 넘겨 문맥도 이어집니다.

* rumps(메뉴바 앱)와 충돌하지 않도록 '별도 프로그램'으로 실행됩니다.
"""

import array
import math
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from datetime import datetime

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QLabel,
                               QPushButton, QTextEdit, QVBoxLayout, QWidget)

from features import config, transcribe, translate

LANG_OPTIONS = [("한국어", "ko"), ("English", "en"), ("日本語", "ja"), ("中文", "zh")]

SEGMENT_SEC = 2        # 잘게 듣는 단위 (짧을수록 반응 빠름)
MAX_BUFFER_SEC = 10    # 말이 계속 이어져도 최대 이 길이마다 한 번 인식
GATE_MIN = 150         # '조용함' 판단 최소 기준. 실제 기준은 주변 소음에 맞춰
                       # 자동으로 올라갑니다 (조용한 방에서 작게 말해도 인식되게)


def _rms(frames: bytes) -> int:
    """16비트 PCM의 소리 크기(RMS). (audioop은 파이썬 3.13에서 제거되어 직접 계산)"""
    if not frames:
        return 0
    samples = array.array("h", frames[: len(frames) // 2 * 2])
    if not samples:
        return 0
    return int(math.sqrt(sum(s * s for s in samples) / len(samples)))


def _tail_rms(path: str, tail_sec: float = 0.5) -> int:
    """조각 끝부분의 소리 크기 (말이 멈췄는지 판단용)."""
    try:
        with wave.open(path) as w:
            rate, n = w.getframerate(), w.getnframes()
            take = min(n, int(rate * tail_sec))
            if take <= 0:
                return 0
            w.setpos(n - take)
            return _rms(w.readframes(take))
    except Exception:
        return 10 ** 6         # 판단 불가 시 '말하는 중'으로 취급


def _max_rms(path: str) -> int:
    try:
        with wave.open(path) as w:
            return _rms(w.readframes(w.getnframes()))
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
        self._gate = GATE_MIN   # '조용함' 기준 (주변 소음에 맞춰 자동 조정)
        self._rms_hist = []     # 최근 조각들의 소리 크기 기록
        self._tmpdir = None     # 소리 조각 임시 폴더 (나만 읽을 수 있게 만들어짐)

    def _resolve_mic(self):
        """장치 '이름'으로 최신 번호를 다시 찾습니다.
        (이어폰을 꽂거나 빼면 번호가 바뀌기 때문)"""
        import sounddevice as sd
        want = self.win.mic_name()
        try:
            devs = sd.query_devices()
        except Exception:
            return None
        for i, d in enumerate(devs):
            if d["max_input_channels"] > 0 and d["name"] == want:
                return i
        return None   # None = 시스템 기본 입력

    def _write_seg(self, idx, pcm):
        path = os.path.join(self._tmpdir, f"seg_{idx:04d}.wav")
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(pcm)
        return path

    def run(self):
        import queue as _queue

        import sounddevice as sd

        self._tmpdir = tempfile.mkdtemp(prefix="kit_live_")

        # 첫 문장부터 빨리 나오도록 인식 모델을 미리 올려둡니다
        self.status.emit("음성인식 준비 중… (잠시만요)")
        try:
            transcribe._get_model()
        except Exception as e:
            self.status.emit("음성인식 모델 오류: " + str(e))
            return

        # CoreAudio로 마이크를 직접 받습니다 (ffmpeg avfoundation은
        # 소리를 조용히 버리는 문제가 있어 쓰지 않습니다)
        q = _queue.Queue()

        def callback(indata, frames, time_info, status):
            q.put(bytes(indata))

        try:
            stream = sd.InputStream(device=self._resolve_mic(), channels=1,
                                    samplerate=16000, dtype="int16",
                                    callback=callback)
            stream.start()
        except Exception as e:
            self.status.emit("마이크를 열지 못했어요: " + str(e))
            return
        self.status.emit("듣는 중… 말씀하세요 (말을 잠깐 멈추면 자막이 떠요)")

        buffer = []          # 아직 인식 안 한 조각들
        buffer_sec = 0
        speaking = False     # 방금까지 말소리가 들렸는지 (상태 표시용)
        acc = b""            # 지금 모으는 중인 조각
        seg_bytes = 16000 * 2 * SEGMENT_SEC
        seg_idx = 0

        while self._running:
            try:
                acc += q.get(timeout=0.3)
            except _queue.Empty:
                continue
            if len(acc) < seg_bytes:
                continue
            f = self._write_seg(seg_idx, acc[:seg_bytes])
            acc = acc[seg_bytes:]
            seg_idx += 1
            buffer.append(f)
            buffer_sec += SEGMENT_SEC

            # '조용함' 기준을 주변 소음에 맞춰 자동 조정:
            # 최근 조각들 중 조용한 편(하위 25%)의 2.5배를 기준으로 삼되,
            # 최소 GATE_MIN 밑으로는 내려가지 않게.
            rms = _max_rms(f)
            self._rms_hist = (self._rms_hist + [rms])[-30:]
            floor = sorted(self._rms_hist)[len(self._rms_hist) // 4]
            # 말을 오래 이어가면 기준선이 말소리까지 올라가므로 상한을 둠
            self._gate = max(GATE_MIN, min(int(floor * 2.5), 600))

            # 말소리 감지 여부를 상태줄로 알려줌 (마이크가 듣고 있다는 확인)
            if rms > self._gate and not speaking:
                speaking = True
                self.status.emit("말소리 감지 — 잠깐 멈추면 자막이 떠요")
            elif rms <= self._gate and speaking:
                speaking = False

            # 말이 멈췄거나(조각 끝이 조용) 버퍼가 가득 → 한 번에 인식
            if _tail_rms(f) < self._gate or buffer_sec >= MAX_BUFFER_SEC:
                self._flush(buffer)
                buffer, buffer_sec = [], 0

        # 중지 → 남은 소리 마저 처리
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass
        if acc:
            buffer.append(self._write_seg(seg_idx, acc))
        self._flush(buffer)
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _flush(self, chunk_files):
        chunk_files = [f for f in chunk_files if os.path.exists(f)]
        if not chunk_files:
            return
        try:
            # 전부 조용한 조각이면 인식할 필요 없음
            # (기준을 넘는 소리가 있으면 Whisper VAD가 한 번 더 걸러줍니다)
            if max(_max_rms(f) for f in chunk_files) < self._gate:
                return
            merged = os.path.join(self._tmpdir, "merged.wav")
            _concat_wavs(chunk_files, merged)
            src, tgt = self.win.src_code(), self.win.tgt_code()
            text = transcribe.transcribe_live(merged, src, self.prev_text)
            if text.strip():
                self.prev_text = (self.prev_text + " " + text)[-300:]
                tr = translate.translate(text, src, tgt) if src != tgt else text
                self.result.emit(text, tr)
                if self._running:
                    self.status.emit("듣는 중… 말씀하세요")
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
        self.save_btn = QPushButton("저장")
        self.save_btn.clicked.connect(self.save)
        top.addWidget(self.save_btn)
        layout.addLayout(top)

        # 2줄: 마이크 선택 + 글자 크기 + 지우기
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("마이크"))
        self.mic_combo = QComboBox()
        try:
            import sounddevice as sd
            devs = sd.query_devices()
            default_in = sd.default.device[0]
        except Exception:
            devs, default_in = [], -1
        for i, d in enumerate(devs):
            if d["max_input_channels"] > 0:
                self.mic_combo.addItem(d["name"], i)
                if i == default_in:
                    self.mic_combo.setCurrentIndex(self.mic_combo.count() - 1)
        self.mic_combo.currentIndexChanged.connect(self._mic_changed)
        row2.addWidget(self.mic_combo)
        row2.addStretch()
        for label, delta in [("A−", -2), ("A+", +2)]:
            b = QPushButton(label)
            b.setFixedWidth(44)
            b.clicked.connect(lambda _=False, d=delta: self.change_font(d))
            row2.addWidget(b)
        clear_btn = QPushButton("지우기")
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
            self.status_lbl.setText("중지됨. '▶ 시작'을 누르면 다시 들어요.")
            self.toggle_btn.setText("▶ 시작")
        else:
            self.start()

    def on_result(self, original, translated):
        self.view.append(f"{original}\n→ {translated}\n")
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
