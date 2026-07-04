"""Kit 설정 저장 (config.json).

저장 폴더, 첫 실행 여부 같은 사용자 설정을 프로젝트 폴더의
config.json 에 보관합니다. (없으면 기본값 사용)
"""

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"

DEFAULTS = {
    "save_dir": str(Path.home() / "Desktop"),   # 캡처·녹화·녹음 저장 위치
    "first_run_done": False,                     # 첫 실행 환영 안내를 봤는지
}


def load() -> dict:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    merged = dict(DEFAULTS)
    merged.update(data)
    return merged


def save(cfg: dict):
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2),
                           encoding="utf-8")


def get(key):
    return load()[key]


def set(key, value):
    cfg = load()
    cfg[key] = value
    save(cfg)


def save_dir() -> Path:
    """저장 폴더를 Path로 돌려줍니다. (없으면 만들어 줌)"""
    p = Path(load()["save_dir"]).expanduser()
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        p = Path.home() / "Desktop"   # 폴더가 사라졌으면 바탕화면으로 복귀
        p.mkdir(parents=True, exist_ok=True)
    return p
