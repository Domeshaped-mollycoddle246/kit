"""화면 캡처 기능.

맥에 기본으로 들어있는 'screencapture' 명령을 사용합니다. (추가 설치 불필요)
캡처한 이미지는 설정된 저장 폴더(기본: 바탕화면)에 저장됩니다.
"""

import os
import subprocess
from datetime import datetime

from features import config


def _new_path() -> str:
    """저장할 새 파일 경로를 만들어 줍니다. (예: 캡처_20260626_143015.png)"""
    name = datetime.now().strftime("캡처_%Y%m%d_%H%M%S.png")
    return str(config.save_dir() / name)


def _preview(path: str):
    """캡처가 잘 됐으면 미리보기(Preview)로 바로 열어 보여줍니다."""
    if os.path.exists(path) and os.path.getsize(path) > 0:
        subprocess.run(["open", path])


def capture_area():
    """마우스로 영역을 드래그해서 캡처하고, 바로 미리보기로 보여줍니다."""
    path = _new_path()
    # -i : 마우스로 영역/창을 직접 선택
    subprocess.run(["screencapture", "-i", path])
    _preview(path)


def capture_full():
    """전체 화면을 캡처하고, 바로 미리보기로 보여줍니다."""
    path = _new_path()
    subprocess.run(["screencapture", path])
    _preview(path)


def capture_window():
    """클릭한 창 하나를 캡처하고, 바로 미리보기로 보여줍니다."""
    path = _new_path()
    # -w : 창 선택 모드 (마우스로 창을 클릭)
    subprocess.run(["screencapture", "-w", path])
    _preview(path)


def open_folder():
    """캡처가 저장되는 폴더를 Finder로 엽니다."""
    subprocess.run(["open", str(config.save_dir())])


def capture_area_for_edit():
    """영역을 캡처하고, 저장된 파일 경로를 돌려줍니다.
    (편집창에서 모자이크/오버레이를 하기 위해 사용)
    캡처를 취소하면 None 을 돌려줍니다."""
    path = _new_path()
    subprocess.run(["screencapture", "-i", path])
    return path if os.path.exists(path) else None
