"""화면 녹화 (화면 + 마이크 소리).

start() 로 시작하고 stop() 으로 끝냅니다. 결과는 저장 폴더에 mov로 저장.
* 시스템에서 나는 소리(유튜브 등)는 마이크로 들어가지 않습니다.
  회의 상대 목소리까지 녹음하려면 나중에 'BlackHole' 설정이 필요해요.

구현 메모:
  ffmpeg(avfoundation)은 이 환경에서 마이크 소리를 조용히 버려서
  (약 15~20%) 소리가 깨지고 영상과 점점 어긋났습니다.
  그래서 맥에 내장된 'screencapture -v -g'(애플 자체 캡처 엔진)를 씁니다.
  → 실측 결과 싱크 오차 ±35ms, 소리 손실 0.
"""

import signal
import subprocess
from datetime import datetime

from features import config, denoise

_proc = None       # 실행 중인 screencapture 프로세스
_outfile = None    # 저장 경로


def is_recording() -> bool:
    return _proc is not None


def start() -> str:
    """녹화를 시작하고 저장될 파일 경로를 돌려줍니다."""
    global _proc, _outfile
    if _proc:
        return _outfile

    _outfile = str(config.save_dir() /
                   datetime.now().strftime("녹화_%Y%m%d_%H%M%S.mov"))
    # -v 화면 녹화, -g 기본 마이크 소리 포함, -k 클릭 표시
    _proc = subprocess.Popen(
        ["screencapture", "-v", "-g", "-k", _outfile],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return _outfile


def stop():
    """녹화를 멈추고 저장된 파일 경로를 돌려줍니다."""
    global _proc, _outfile
    if not _proc:
        return None
    try:
        # Ctrl-C 와 같은 신호 → 파일을 정상적으로 마무리하고 종료
        _proc.send_signal(signal.SIGINT)
        _proc.wait(timeout=15)
    except Exception:
        _proc.terminate()
        try:
            _proc.wait(timeout=5)
        except Exception:
            _proc.kill()
    out = _outfile
    _proc = None
    _outfile = None
    # 마이크 잡음 제거 (영상은 그대로 복사, 실패해도 원본 유지)
    denoise.clean_video_audio(out)
    return out
