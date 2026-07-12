"""음성 녹음 (마이크만).

start() 로 시작, stop() 으로 끝냄. 결과는 저장 폴더에 m4a로 저장.

구현 메모:
  ffmpeg(avfoundation)은 이 환경에서 마이크 소리를 조용히 버려서(15~20%)
  녹음이 깨졌습니다. 그래서 CoreAudio(sounddevice)로 직접 받습니다.
  멈출 때 잡음 제거(RNNoise)를 거쳐 m4a로 저장합니다.
"""

import os
import queue
import tempfile
import threading
import wave
from datetime import datetime
from pathlib import Path

from features import config, denoise

_stream = None      # 실행 중인 CoreAudio 입력 스트림
_writer = None      # wav 저장 스레드
_queue = None
_outfile = None     # 최종 m4a 경로
_tmpwav = None      # 녹음 중인 임시 wav (나만 읽을 수 있게 만들어짐)

SAMPLE_RATE = 48000


def is_recording() -> bool:
    return _stream is not None


def _pick_device():
    """맥북 내장 마이크를 우선으로 고릅니다 (없으면 시스템 기본 입력)."""
    import sounddevice as sd
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0 and (
                "MacBook" in d["name"] and "마이크" in d["name"]
                or "Built-in" in d["name"]):
            return i
    return None   # None = 시스템 기본 입력


def start() -> str:
    """녹음을 시작하고 저장될 파일 경로를 돌려줍니다."""
    global _stream, _writer, _queue, _outfile, _tmpwav
    if _stream:
        return _outfile

    import sounddevice as sd

    _outfile = str(config.save_dir() /
                   datetime.now().strftime("녹음_%Y%m%d_%H%M%S.m4a"))
    _queue = queue.Queue()

    fd, _tmpwav = tempfile.mkstemp(prefix="kit_rec_", suffix=".wav")
    os.close(fd)
    wav = wave.open(_tmpwav, "wb")
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(SAMPLE_RATE)

    q = _queue

    def writer():
        # 콜백(실시간 스레드)을 가볍게 유지하려고 파일 쓰기는 여기서 합니다
        while True:
            data = q.get()
            if data is None:
                break
            wav.writeframes(data)
        wav.close()

    def callback(indata, frames, time_info, status):
        q.put(bytes(indata))

    stream = sd.InputStream(device=_pick_device(), channels=1,
                            samplerate=SAMPLE_RATE, dtype="int16",
                            callback=callback)
    stream.start()

    _writer = threading.Thread(target=writer, daemon=True)
    _writer.start()
    _stream = stream
    return _outfile


def stop():
    """녹음을 멈추고 저장된 파일 경로를 돌려줍니다."""
    global _stream, _writer, _queue, _outfile, _tmpwav
    if not _stream:
        return None

    try:
        _stream.stop()
        _stream.close()
    except Exception:
        pass
    _queue.put(None)          # 저장 스레드 종료 신호
    _writer.join(timeout=10)

    out = _outfile
    tmp = _tmpwav
    _stream = _writer = _queue = None
    _outfile = _tmpwav = None

    # 잡음 제거 + m4a 변환 (실패하면 잡음 제거 없이 변환만)
    if not denoise.clean_audio_file(tmp, out):
        import subprocess
        subprocess.run([denoise.FFMPEG, "-hide_banner", "-y",
                        "-i", tmp, "-c:a", "aac", "-b:a", "192k", out],
                       capture_output=True)
    try:
        Path(tmp).unlink()
    except Exception:
        pass
    return out
