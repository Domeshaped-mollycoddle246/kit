"""로그인 시 자동 시작 (macOS LaunchAgent).

켜면: ~/Library/LaunchAgents/com.commme.kit.plist 를 만들어
다음 로그인부터 Kit이 자동으로 켜집니다.
끄면: 그 파일을 지웁니다. (지금 켜져 있는 Kit에는 영향 없음)
"""

from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
PLIST = Path.home() / "Library" / "LaunchAgents" / "com.commme.kit.plist"


def is_enabled() -> bool:
    return PLIST.exists()


def enable():
    python = APP_DIR / ".venv" / "bin" / "python"
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.commme.kit</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>{APP_DIR / "app.py"}</string>
    </array>
    <key>WorkingDirectory</key><string>{APP_DIR}</string>
    <key>RunAtLoad</key><true/>
    <key>StandardOutPath</key><string>/tmp/kit_autostart.log</string>
    <key>StandardErrorPath</key><string>/tmp/kit_autostart.log</string>
</dict>
</plist>
"""
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    PLIST.write_text(plist, encoding="utf-8")


def disable():
    try:
        PLIST.unlink()
    except FileNotFoundError:
        pass
