"""바탕화면 청소 기능.

바탕화면에 흩어진 '파일'들을 종류별로 정리해서
'정리됨_날짜' 폴더 안으로 옮깁니다. (삭제하지 않으므로 안전합니다)
폴더는 건드리지 않습니다.
"""

import shutil
from datetime import datetime
from pathlib import Path

DESKTOP = Path.home() / "Desktop"

# 확장자별 분류 규칙
CATEGORIES = {
    "이미지": [".png", ".jpg", ".jpeg", ".gif", ".heic", ".webp", ".bmp", ".tiff"],
    "동영상": [".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"],
    "음악": [".mp3", ".wav", ".m4a", ".aac", ".flac"],
    "문서": [".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
             ".txt", ".hwp", ".hwpx", ".key", ".pages", ".numbers", ".csv"],
    "압축": [".zip", ".rar", ".7z", ".tar", ".gz", ".dmg"],
}


def _category(ext: str) -> str:
    """확장자를 보고 어느 카테고리인지 알려줍니다."""
    ext = ext.lower()
    for cat, exts in CATEGORIES.items():
        if ext in exts:
            return cat
    return "기타"


def _safe_dest(dest_dir: Path, name: str) -> Path:
    """같은 이름의 파일이 이미 있으면 (1), (2) 를 붙여 겹치지 않게 합니다."""
    dest = dest_dir / name
    if not dest.exists():
        return dest
    stem, suffix = Path(name).stem, Path(name).suffix
    i = 1
    while True:
        candidate = dest_dir / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def clean_desktop() -> tuple[int, int]:
    """바탕화면 정리를 실행합니다.

    반환값: (옮긴 파일 수, 그대로 둔 폴더 수)
    """
    archive = DESKTOP / datetime.now().strftime("정리됨_%Y%m%d")
    moved = 0
    skipped_folders = 0

    for item in DESKTOP.iterdir():
        # 숨김파일과 이전에 만든 '정리됨_' 폴더는 건너뜀
        if item.name.startswith(".") or item.name.startswith("정리됨_"):
            continue
        # 폴더는 건드리지 않음
        if item.is_dir():
            skipped_folders += 1
            continue

        cat = _category(item.suffix)
        dest_dir = archive / cat
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = _safe_dest(dest_dir, item.name)
        shutil.move(str(item), str(dest))
        moved += 1

    return moved, skipped_folders
