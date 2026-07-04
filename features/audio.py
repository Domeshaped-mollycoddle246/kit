"""음성 녹음 (마이크만).

start() 로 시작, stop() 으로 끝냄. 결과는 바탕화면에 m4a로 저장.
회의록(다음 단계)에서 이 녹음 파일을 글자로 바꿀 거예요.
"""

import subprocess
from datetime import datetime

from features import avdevices, config

_proc = None
_outfile = None


def is_recording() -> bool:
    return _proc is not None


def start() -> str:
    """녹음을 시작하고 저장될 파일 경로를 돌려줍니다."""
    global _proc, _outfile
    if _proc:
        return _outfile

    _, audio = avdevices.list_devices()
    mic = avdevices.find_mic(audio)
    if mic is None:
        raise RuntimeError("마이크를 찾지 못했어요.")

    _outfile = str(config.save_dir() / datetime.now().strftime("녹음_%Y%m%d_%H%M%S.m4a"))

    cmd = [
        avdevices.FFMPEG, "-hide_banner", "-y",
        "-f", "avfoundation", "-i", f":{mic}",   # 영상 없이 소리만
        "-c:a", "aac", "-b:a", "192k", _outfile,
    ]
    _proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return _outfile


def stop():
    """녹음을 멈추고 저장된 파일 경로를 돌려줍니다."""
    global _proc, _outfile
    if not _proc:
        return None
    try:
        _proc.communicate(input=b"q", timeout=15)
    except Exception:
        _proc.terminate()
        try:
            _proc.wait(timeout=5)
        except Exception:
            _proc.kill()
    out = _outfile
    _proc = None
    _outfile = None
    return out
