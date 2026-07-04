"""ffmpeg(avfoundation)로 맥의 화면/마이크 장치 번호를 찾아주는 도우미.

장치 번호는 외부기기를 꽂고 뺄 때 바뀔 수 있어서, 녹화할 때마다 새로 확인합니다.
"""

import re
import subprocess
from pathlib import Path

# 프로젝트 폴더 안 bin/ffmpeg
FFMPEG = str(Path(__file__).resolve().parent.parent / "bin" / "ffmpeg")


def list_devices():
    """현재 연결된 영상/소리 장치 목록을 돌려줍니다.
    반환: (video, audio) — 각각 {번호: 이름} 사전"""
    result = subprocess.run(
        [FFMPEG, "-hide_banner", "-f", "avfoundation",
         "-list_devices", "true", "-i", ""],
        capture_output=True, text=True)
    out = result.stderr  # ffmpeg는 목록을 stderr로 출력
    video, audio = {}, {}
    section = None
    for line in out.splitlines():
        if "video devices" in line:
            section = "v"
            continue
        if "audio devices" in line:
            section = "a"
            continue
        m = re.search(r"\]\s*\[(\d+)\]\s+(.+)$", line)
        if m and section:
            idx, name = int(m.group(1)), m.group(2).strip()
            (video if section == "v" else audio)[idx] = name
    return video, audio


def find_screen(video: dict):
    """'Capture screen' 항목(화면)을 찾아 번호를 돌려줍니다."""
    for idx, name in video.items():
        if "Capture screen" in name:
            return idx
    return None


def find_mic(audio: dict):
    """내장 마이크를 우선으로 찾고, 없으면 첫 소리 장치를 돌려줍니다."""
    for idx, name in audio.items():
        if any(k in name for k in ("마이크", "Microphone", "Built-in", "MacBook")):
            return idx
    return next(iter(audio), None)
