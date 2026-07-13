#!/bin/bash
# 이 파일을 더블클릭하면 Kit 앱이 켜집니다.
# 처음 실행이면 필요한 것들(파이썬 환경, AI 모델)을 자동으로 설치한 뒤 켜져요.
# 켜진 뒤에는 이 검은 터미널 창을 닫아도 앱은 계속 살아있어요.
cd "$(dirname "$0")"

fail() {   # 오류 메시지를 보여주고, 사용자가 읽을 시간을 준 뒤 종료
  echo ""
  echo "$1"
  read -n1 -s -p "아무 키나 누르면 창이 닫혀요..." 2>/dev/null || sleep 15
  exit 1
}

# ---------- 0) 맥/파이썬 버전 확인 ----------
MACV=$(sw_vers -productVersion | cut -d. -f1)
if [ "$MACV" -lt 11 ] 2>/dev/null; then
  fail "❌ 이 앱은 macOS 11(빅서) 이상에서 동작해요.
   지금 맥은 macOS $(sw_vers -productVersion)라서 음성인식 엔진이 설치되지 않아요."
fi

if ! command -v python3 >/dev/null 2>&1; then
  xcode-select --install 2>/dev/null
  fail "❌ 파이썬(python3)이 없어요.
   방금 뜬 설치 안내 창에서 '설치'를 누르고, 끝나면 이 파일을 다시 더블클릭해 주세요."
fi

# 파이썬 3.9 이상 필요 (오래된 맥의 기본 파이썬은 3.8일 수 있음)
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
  fail "❌ 파이썬 버전이 너무 낮아요 ($(python3 -V 2>&1)). 3.9 이상이 필요해요.
   해결법: https://www.python.org/downloads/ 에서 최신 파이썬을 설치한 뒤
   이 파일을 다시 더블클릭해 주세요."
fi

# ---------- 1) 처음 실행이면 파이썬 환경 자동 설치 ----------
if [ ! -x .venv/bin/python ]; then
  echo "🛠  처음 실행이네요! 파이썬 환경을 만드는 중… (몇 분 걸려요)"
  python3 -m venv .venv || fail "❌ 파이썬 환경 생성에 실패했어요."
  .venv/bin/pip install --upgrade pip -q

  # 화면 라이브러리(PySide6)는 맥 버전마다 설치 가능한 버전이 달라요:
  #   macOS 13+ → 6.10.3 / macOS 12 → 6.9.1 / macOS 11 → 6.7.3
  REQS=requirements.txt
  if [ "$MACV" -eq 12 ]; then
    sed 's/^PySide6==[0-9.]*/PySide6==6.9.1 /' requirements.txt > /tmp/kit_reqs.txt; REQS=/tmp/kit_reqs.txt
  elif [ "$MACV" -eq 11 ]; then
    sed 's/^PySide6==[0-9.]*/PySide6==6.7.3 /' requirements.txt > /tmp/kit_reqs.txt; REQS=/tmp/kit_reqs.txt
  fi

  .venv/bin/pip install -r "$REQS" \
    || fail "❌ 패키지 설치에 실패했어요 — 인터넷 연결을 확인하고 다시 실행해 주세요."
fi

# ---------- 2) AI 모델·ffmpeg가 없으면 자동 다운로드 ----------
if [ ! -x bin/ffmpeg ] || [ ! -f models/faster-whisper-small/model.bin ] \
   || [ ! -d models/argos/ko_en ]; then
  echo "📦 AI 모델을 내려받는 중… (약 1GB — 인터넷 속도에 따라 몇 분에서 수십 분)"
  bash scripts/download_assets.sh \
    || fail "❌ 다운로드에 실패했어요 — 인터넷 연결을 확인하고 다시 실행해 주세요.
   (이미 받은 부분은 건너뛰니 다시 실행하면 이어서 받아요)"
fi

# ---------- 3) 실행 ----------
# 이미 켜져 있으면 중복 실행하지 않음 (대소문자 무관하게 확인)
if pgrep -f "[Pp]ython app.py" >/dev/null; then
  echo "✅ Kit이 이미 켜져 있어요. (메뉴바 위쪽 당근 아이콘 확인)"
else
  # venv 파이썬을 직접 사용 — 폴더를 옮겨도 activate 경로 문제로 깨지지 않음
  nohup .venv/bin/python app.py >/tmp/biseo.log 2>&1 &
  disown
  echo "✅ Kit을 켰어요! 메뉴바(화면 맨 위) 오른쪽에서 당근 아이콘을 찾으세요."
fi

echo "이 창은 닫아도 됩니다."
sleep 2
