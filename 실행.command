#!/bin/bash
# 이 파일을 더블클릭하면 Kit 앱이 켜집니다.
# 켜진 뒤에는 이 검은 터미널 창을 닫아도 앱은 계속 살아있어요.
cd "$(dirname "$0")"
source .venv/bin/activate

# 이미 켜져 있으면 중복 실행하지 않음 (대소문자 무관하게 확인)
if pgrep -f "[Pp]ython app.py" >/dev/null; then
  echo "✅ Kit이 이미 켜져 있어요. (메뉴바 위쪽 'Kit' 확인)"
else
  nohup python app.py >/tmp/biseo.log 2>&1 &
  disown
  echo "✅ Kit을 켰어요! 메뉴바(화면 맨 위) 오른쪽에서 'Kit'을 찾으세요."
fi

echo "이 창은 닫아도 됩니다."
sleep 2
