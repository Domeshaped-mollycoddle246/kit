"""녹음(음성) → 글자(텍스트) 변환.

무료 오프라인 엔진 'faster-whisper'를 사용합니다. (인터넷 전송 없음)
* 맨 처음 한 번은 인식 모델(약 460MB)을 자동 내려받아요 — 몇 분 걸릴 수 있어요.
  그 다음부터는 바로 변환됩니다.
"""

from pathlib import Path

# 모델은 한 번만 메모리에 올려두고 재사용
_model = None

# 프로젝트 안에 미리 받아둔 모델 폴더 (인터넷 다운로드 불필요)
LOCAL_MODEL = Path(__file__).resolve().parent.parent / "models" / "faster-whisper-small"


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        # 로컬에 받아둔 모델이 있으면 그걸, 없으면 이름으로(인터넷) 불러옵니다.
        source = str(LOCAL_MODEL) if LOCAL_MODEL.exists() else "small"
        # 맥(애플실리콘)에서는 CPU + int8 이 가장 무난합니다.
        _model = WhisperModel(source, device="cpu", compute_type="int8")
    return _model


def _fmt(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def transcribe_to_file(audio_path: str, language: str = "ko") -> str:
    """오디오 파일을 글자로 바꿔 '..._텍스트.txt' 로 저장하고 그 경로를 돌려줍니다.

    language="ko" 는 한국어. 영어 회의면 "en", 자동감지는 None.
    """
    model = _get_model()
    # beam_size=5 : 정확도 향상 (조금 느려지지만 오타가 줄어요)
    segments, info = model.transcribe(audio_path, language=language,
                                      vad_filter=True, beam_size=5)

    lines = []
    for seg in segments:
        lines.append(f"[{_fmt(seg.start)}] {seg.text.strip()}")
    text = "\n".join(lines) if lines else "(인식된 음성이 없습니다)"

    out = str(Path(audio_path).with_suffix("")) + "_텍스트.txt"
    Path(out).write_text(text, encoding="utf-8")
    return out


def transcribe_live(audio_path: str, language: str = "ko",
                    prev_text: str = "") -> str:
    """실시간 통역용 인식.

    - prev_text: 직전에 인식된 문장을 힌트로 줘서 문맥이 이어지게 함
    - 조용한 구간에서 나오는 '환청'(엉뚱한 문장)을 걸러냄
    """
    model = _get_model()
    segments, info = model.transcribe(
        audio_path, language=language, vad_filter=True, beam_size=5,
        initial_prompt=(prev_text[-200:] if prev_text else None),
        condition_on_previous_text=False)
    parts = []
    for seg in segments:
        # 말이 아닐 확률이 높고 자신감도 낮으면 환청으로 보고 버림
        if seg.no_speech_prob > 0.6 and seg.avg_logprob < -0.7:
            continue
        parts.append(seg.text.strip())
    return " ".join(parts).strip()


def transcribe_plain(audio_path: str, language: str = "ko",
                     beam_size: int = 5) -> str:
    """오디오를 글자로 바꿔 '순수 텍스트'만 돌려줍니다 (시간표시 없이).
    통역·실시간 통역에서 사용."""
    model = _get_model()
    segments, info = model.transcribe(audio_path, language=language,
                                      vad_filter=True, beam_size=beam_size)
    return " ".join(seg.text.strip() for seg in segments).strip()
