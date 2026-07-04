# Kit — 개인용 맥 도구 모음

맥 **메뉴바**에 사는 작은 도구 모음 앱입니다. 캡처·녹화·녹음·글자변환·통역·번역을
한 곳에서 해결합니다. AI 기능(음성인식·번역)은 **인터넷·API 키 없이 컴퓨터 안에서** 동작해요.

> ⚠️ **macOS 전용** (Apple Silicon 권장). 현재 Windows·Linux는 지원하지 않습니다. → [지원 환경](#지원-환경)

## 기능

| 카테고리 | 기능 |
|---|---|
| 📸 캡처 | 영역/전체/창 캡처, 캡처 후 편집(자르기·모자이크·화살표·박스·펜·글자), 폴더 열기 |
| 🎬 녹화·녹음 | 화면 녹화(화면+마이크), 음성 녹음, 녹음 → 글자(텍스트) 변환 |
| 🗣️ 통역·번역 | 통역(말→번역), **실시간 통역 창**, 글 번역(한·영·일·중) |
| 🌐 웹 도구 | 자주 쓰는 웹 도구 바로가기 |
| 🧹 청소 | 바탕화면 파일 종류별 자동 정리 |
| ⚙️ 설정 | 로그인 시 자동 시작, 저장 폴더 변경 |

## 폴더 구조

```
kit/
├─ app.py              # 메뉴바 앱 본체
├─ editor.py           # 캡처 편집창 (PySide6)
├─ live_interpret.py   # 실시간 통역 창 (PySide6)
├─ features/           # 기능별 모듈
│   ├─ capture.py      # 캡처
│   ├─ cleanup.py      # 바탕화면 청소
│   ├─ record.py       # 화면 녹화
│   ├─ audio.py        # 음성 녹음
│   ├─ avdevices.py    # 화면/마이크 장치 감지
│   ├─ transcribe.py   # 음성 → 글자 (Whisper)
│   ├─ translate.py    # 번역 (Argos, 오프라인)
│   ├─ config.py       # 설정 저장 (저장 폴더 등)
│   └─ autostart.py    # 로그인 시 자동 시작
├─ assets/             # 메뉴바 아이콘
├─ bin/ffmpeg          # 녹화/녹음용 (download_assets.sh 로 받음)
├─ models/             # AI 모델 (download_assets.sh 로 받음)
├─ scripts/
│   └─ download_assets.sh
├─ requirements.txt
└─ 실행.command        # 더블클릭으로 앱 켜기
```

## 처음 설치 (새 맥)

```bash
git clone https://github.com/commme/kit.git
cd kit
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bash scripts/download_assets.sh      # ffmpeg + AI 모델 다운로드
```

## 실행

`실행.command` 더블클릭 → 메뉴바(화면 맨 위)에 **"비서"** 가 나타납니다.
끄려면: 메뉴 → 종료.

## 권한 (한 번만)

- **캡처/화면 녹화**: 캡처나 녹화를 한 번 시도한 뒤 → 시스템 설정 → 개인정보 보호 및 보안 →
  **화면 및 시스템 오디오 기록** 목록에 나타난 항목(**터미널** 또는 **Python**)을 켜고, 앱을 재시작하세요.
- **녹음/통역**: 첫 사용 시 **마이크** 권한 허용

## 지원 환경

- ✅ **macOS** (Apple Silicon에서 개발·테스트). Intel 맥은 미검증.
- ❌ **Windows / Linux**: 현재 미지원.
  - 메뉴바·화면캡처·녹화·녹음 등이 macOS 전용 기술(rumps, screencapture, avfoundation 등)에 의존합니다.
  - 음성인식(faster-whisper)·번역(ctranslate2)·이미지편집(Pillow) **로직**은 크로스플랫폼이라, 윈도우판은 UI·캡처 계층만 새로 구현하면 가능합니다. (향후 과제)

## 참고

- 번역 품질: 한↔영 좋음 · 한↔일 양호 · 한↔중 보통 (무료·오프라인 한계)
- 실시간 통역은 "완전 동시통역"이 아니라 몇 초 따라오는 **거의 실시간**입니다.
