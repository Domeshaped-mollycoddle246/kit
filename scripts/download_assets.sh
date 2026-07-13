#!/bin/bash
# 용량 큰 자료(ffmpeg, 음성인식 모델, 잡음제거 모델, 번역 언어팩)를 내려받습니다.
# 이미 받아둔 항목은 건너뛰므로, 중간에 실패해도 다시 실행하면 이어서 받아요.
set -e
cd "$(dirname "$0")/.."   # 프로젝트 폴더로 이동
echo "프로젝트 폴더: $(pwd)"

# ---------- 1) ffmpeg (녹음 변환/잡음제거용) ----------
if [ -x bin/ffmpeg ]; then
  echo "✔ ffmpeg — 이미 있음, 건너뜀"
else
  echo "▶ ffmpeg 내려받는 중…"
  mkdir -p bin
  # 맥 종류(Apple Silicon/Intel)에 맞는 빌드를 골라요
  case "$(uname -m)" in
    arm64)  FF_ARCH="arm64" ;;
    *)      FF_ARCH="amd64" ;;   # Intel 맥
  esac
  # '최신' 링크가 가리키는 실제 파일 주소를 알아낸 뒤,
  # 배포처가 함께 올려둔 SHA256 체크섬으로 파일이 손상·변조되지 않았는지 확인합니다.
  FF_URL=$(curl -s -o /dev/null -w "%{url_effective}" -L -r 0-0 \
    "https://ffmpeg.martin-riedl.de/redirect/latest/macos/$FF_ARCH/release/ffmpeg.zip")
  curl -fL "$FF_URL" -o /tmp/ffmpeg.zip
  curl -fL "${FF_URL}.sha256" -o /tmp/ffmpeg.zip.sha256
  echo "$(cat /tmp/ffmpeg.zip.sha256 | cut -d' ' -f1)  /tmp/ffmpeg.zip" | shasum -a 256 -c - \
    || { echo "❌ ffmpeg 체크섬 불일치 — 다운로드가 손상됐어요. 다시 실행해 주세요."; exit 1; }
  unzip -o -q /tmp/ffmpeg.zip -d bin && rm -f /tmp/ffmpeg.zip /tmp/ffmpeg.zip.sha256
  chmod +x bin/ffmpeg
  xattr -dr com.apple.quarantine bin/ffmpeg 2>/dev/null || true
fi

# ---------- 2) Whisper 음성인식 모델 (small) ----------
if [ -f models/faster-whisper-small/model.bin ]; then
  echo "✔ 음성인식 모델 — 이미 있음, 건너뜀"
else
  echo "▶ 음성인식 모델(small, ~480MB) 내려받는 중…"
  mkdir -p models/faster-whisper-small
  # 'main' 대신 특정 버전(커밋)에 고정 → 저장소가 바뀌어도 항상 같은 파일을 받음
  WREV="536b0662742c02347bc0e980a01041f333bce120"
  WBASE="https://huggingface.co/Systran/faster-whisper-small/resolve/$WREV"
  for f in config.json tokenizer.json vocabulary.txt model.bin; do
    curl -fL "$WBASE/$f" -o "models/faster-whisper-small/$f"
  done
fi

# ---------- 3) 잡음제거 모델 (RNNoise, 음성 특화) ----------
if [ -f models/rnnoise_voice.rnnn ]; then
  echo "✔ 잡음제거 모델 — 이미 있음, 건너뜀"
else
  echo "▶ 잡음제거 모델 내려받는 중…"
  mkdir -p models
  RN_URL="https://raw.githubusercontent.com/GregorR/rnnoise-models/master/beguiling-drafter-2018-08-30/bd.rnnn"
  RN_SHA="ae3f7411e1e6a884f839a4a145c394408398f09854dbc1216ee02faafc98a17b"
  curl -fL "$RN_URL" -o models/rnnoise_voice.rnnn
  echo "$RN_SHA  models/rnnoise_voice.rnnn" | shasum -a 256 -c - \
    || { echo "❌ 잡음제거 모델 체크섬 불일치"; rm -f models/rnnoise_voice.rnnn; exit 1; }
fi

# ---------- 4) 번역 언어팩 (한·영·일·중) ----------
echo "▶ 번역 언어팩 확인 중…"
mkdir -p models/argos
get_pack() {   # $1=주소, $2=설치되는 폴더 이름
  if [ -d "models/argos/$2" ]; then
    echo "✔ 언어팩 $2 — 이미 있음, 건너뜀"
    return
  fi
  f="/tmp/$(basename "$1")"
  curl -fL "$1" -o "$f"
  unzip -o -q "$f" -d models/argos
  rm -f "$f"
}
get_pack "https://argos-net.com/v1/translate-ko_en-1_1.argosmodel" ko_en
get_pack "https://argos-net.com/v1/translate-en_ko-1_1.argosmodel" en_ko
get_pack "https://argos-net.com/v1/translate-en_ja-1_1.argosmodel" en_ja
get_pack "https://argos-net.com/v1/translate-ja_en-1_1.argosmodel" ja_en
get_pack "https://argos-net.com/v1/translate-en_zh-1_9.argosmodel" en_zh
get_pack "https://argos-net.com/v1/translate-zh_en-1_9.argosmodel" zh_en
# 신버전(1_9)은 폴더명이 길게 풀려서 이름을 맞춰줍니다
[ -d models/argos/translate-en_zh-1_9 ] && mv models/argos/translate-en_zh-1_9 models/argos/en_zh
[ -d models/argos/translate-zh_en-1_9 ] && mv models/argos/translate-zh_en-1_9 models/argos/zh_en

echo "✅ 모든 자료 준비 완료!"
