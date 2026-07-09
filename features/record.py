"""화면 녹화 (화면 + 마이크 소리).

start() 로 시작하고 stop() 으로 끝냅니다. 결과는 바탕화면에 mp4로 저장.
* 시스템에서 나는 소리(유튜브 등)는 마이크로 들어가지 않습니다.
  회의 상대 목소리까지 녹음하려면 나중에 'BlackHole' 설정이 필요해요.
"""

import subprocess
from datetime import datetime

from features import avdevices, config

_proc = None       # 실행 중인 ffmpeg 프로세스
_outfile = None    # 저장 경로


def is_recording() -> bool:
    return _proc is not None


def start() -> str:
    """녹화를 시작하고 저장될 파일 경로를 돌려줍니다."""
    global _proc, _outfile
    if _proc:
        return _outfile

    video, audio = avdevices.list_devices()
    screen = avdevices.find_screen(video)
    if screen is None:
        raise RuntimeError("화면 장치를 찾지 못했어요.")
    mic = avdevices.find_mic(audio)

    _outfile = str(config.save_dir() / datetime.now().strftime("녹화_%Y%m%d_%H%M%S.mp4"))

    # 화면과 마이크를 한 입력("화면:마이크")으로 받으면 서로 다른 클럭으로
    # 타임스탬프가 찍혀 영상과 소리가 어긋납니다. 입력을 둘로 나누고
    # 둘 다 실제 시계(wallclock) 기준으로 찍어 싱크를 맞춥니다.
    cmd = [avdevices.FFMPEG, "-hide_banner", "-y"]
    cmd += [
        "-f", "avfoundation", "-use_wallclock_as_timestamps", "1",
        "-thread_queue_size", "512",
        "-framerate", "30", "-capture_cursor", "1",
        "-i", f"{screen}:none",
    ]
    if mic is not None:
        cmd += [
            "-f", "avfoundation", "-use_wallclock_as_timestamps", "1",
            "-thread_queue_size", "512",
            "-i", f"none:{mic}",
            "-map", "0:v", "-map", "1:a",
            # 마이크 클럭이 미세하게 빠르거나 느려도 소리를 늘이고 줄여 맞춤
            "-af", "aresample=async=1:first_pts=0",
            "-c:a", "aac",
        ]
    cmd += [
        "-c:v", "h264_videotoolbox", "-b:v", "8000k", "-pix_fmt", "yuv420p",
        "-fps_mode", "vfr",
        _outfile,
    ]
    # stdin을 열어둬서 나중에 'q'를 보내 깔끔하게 멈춥니다.
    _proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return _outfile


def stop():
    """녹화를 멈추고 저장된 파일 경로를 돌려줍니다."""
    global _proc, _outfile
    if not _proc:
        return None
    try:
        _proc.communicate(input=b"q", timeout=15)   # 'q' = 정상 종료
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
