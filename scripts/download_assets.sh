#!/bin/bash
# 용량 큰 자료(ffmpeg, 음성인식 모델, 번역 언어팩)를 내려받습니다.
# 새 컴퓨터에서 처음 설치할 때 한 번 실행하세요.
set -e
cd "$(dirname "$0")/.."   # 프로젝트 폴더로 이동
echo "프로젝트 폴더: $(pwd)"

# ---------- 1) ffmpeg (화면녹화/녹음/실시간통역용) ----------
echo "▶ ffmpeg 내려받는 중…"
mkdir -p bin
curl -fL "https://ffmpeg.martin-riedl.de/redirect/latest/macos/arm64/release/ffmpeg.zip" -o /tmp/ffmpeg.zip
unzip -o -q /tmp/ffmpeg.zip -d bin && rm -f /tmp/ffmpeg.zip
chmod +x bin/ffmpeg
xattr -dr com.apple.quarantine bin/ffmpeg 2>/dev/null || true

# ---------- 2) Whisper 음성인식 모델 (small) ----------
echo "▶ 음성인식 모델(small, ~480MB) 내려받는 중…"
mkdir -p models/faster-whisper-small
WBASE="https://huggingface.co/Systran/faster-whisper-small/resolve/main"
for f in model.bin config.json tokenizer.json vocabulary.txt; do
  curl -fL "$WBASE/$f" -o "models/faster-whisper-small/$f"
done

# ---------- 3) 번역 언어팩 (한·영·일·중) ----------
echo "▶ 번역 언어팩 내려받는 중…"
mkdir -p models/argos
get_pack() {   # $1=주소
  f="/tmp/$(basename "$1")"
  curl -fL "$1" -o "$f"
  unzip -o -q "$f" -d models/argos
  rm -f "$f"
}
get_pack "https://argos-net.com/v1/translate-ko_en-1_1.argosmodel"
get_pack "https://argos-net.com/v1/translate-en_ko-1_1.argosmodel"
get_pack "https://argos-net.com/v1/translate-en_ja-1_1.argosmodel"
get_pack "https://argos-net.com/v1/translate-ja_en-1_1.argosmodel"
get_pack "https://argos-net.com/v1/translate-en_zh-1_9.argosmodel"
get_pack "https://argos-net.com/v1/translate-zh_en-1_9.argosmodel"
# 신버전(1_9)은 폴더명이 길게 풀려서 이름을 맞춰줍니다
[ -d models/argos/translate-en_zh-1_9 ] && mv models/argos/translate-en_zh-1_9 models/argos/en_zh
[ -d models/argos/translate-zh_en-1_9 ] && mv models/argos/translate-zh_en-1_9 models/argos/zh_en

echo "✅ 모든 자료 준비 완료!"
