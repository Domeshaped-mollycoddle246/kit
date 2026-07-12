"""녹음·녹화 소리의 잡음 제거 (RNNoise).

ffmpeg의 arnndn 필터 + 음성 특화 모델(models/rnnoise_voice.rnnn)로
배경 잡음(팬 소리, 웅웅거림 등)을 걸러냅니다. 파일 → 파일 변환이라
실시간 부담이 없고, 실패하면 원본을 그대로 둡니다.
"""

import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

# 프로젝트 폴더 안 bin/ffmpeg (scripts/download_assets.sh 로 받음)
FFMPEG = str(_ROOT / "bin" / "ffmpeg")

MODEL = _ROOT / "models" / "rnnoise_voice.rnnn"

# 75Hz 아래 웅웅거림 제거 + RNNoise 음성 잡음 제거
_FILTER = f"highpass=f=75,arnndn=m='{MODEL}'"


def clean_audio_file(src: str, dst: str) -> bool:
    """소리 파일(wav 등)의 잡음을 걸러 m4a로 저장합니다. 성공하면 True."""
    if not MODEL.exists():
        return False
    r = subprocess.run(
        [FFMPEG, "-hide_banner", "-y", "-i", src,
         "-af", _FILTER, "-c:a", "aac", "-b:a", "192k", dst],
        capture_output=True)
    return r.returncode == 0 and Path(dst).exists() and Path(dst).stat().st_size > 0


def clean_video_audio(path: str) -> bool:
    """영상 파일의 소리 트랙만 잡음 제거해서 제자리 교체합니다. 성공하면 True.
    (영상 트랙은 재인코딩 없이 복사 → 화질 그대로, 빠름)"""
    if not MODEL.exists():
        return False
    src = Path(path)
    tmp = src.with_name(src.stem + "_denoise" + src.suffix)
    r = subprocess.run(
        [FFMPEG, "-hide_banner", "-y", "-i", str(src),
         "-c:v", "copy", "-af", _FILTER, "-c:a", "aac", "-b:a", "192k",
         str(tmp)],
        capture_output=True)
    if r.returncode == 0 and tmp.exists() and tmp.stat().st_size > 0:
        tmp.replace(src)
        return True
    try:
        tmp.unlink()
    except Exception:
        pass
    return False
