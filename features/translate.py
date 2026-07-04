"""번역 (오프라인). 한국어·영어·일본어·중국어 지원.

argos 언어팩을 ctranslate2 + sentencepiece 로 직접 사용합니다.
영어 외 언어끼리는 '영어를 경유(pivot)'해서 번역해요. (예: 한→일 = 한→영→일)
"""

import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "models" / "argos"

# 사람이 읽는 이름
LANGS = {"ko": "한국어", "en": "English", "ja": "日本語", "zh": "中文"}

# (출발어, 도착어) -> 언어팩 폴더 이름
_PACK_DIRS = {
    ("ko", "en"): "ko_en", ("en", "ko"): "en_ko",
    ("ja", "en"): "ja_en", ("en", "ja"): "en_ja",
    ("zh", "en"): "zh_en", ("en", "zh"): "en_zh",
}

_cache = {}   # (src,tgt) -> (translator, sentencepiece)


def available_pairs():
    """실제로 다운로드된 언어팩만 돌려줍니다."""
    return {pair for pair, name in _PACK_DIRS.items() if (BASE / name).exists()}


def _load(src, tgt):
    key = (src, tgt)
    if key not in _cache:
        import ctranslate2
        import sentencepiece
        folder = BASE / _PACK_DIRS[key]
        sp = sentencepiece.SentencePieceProcessor(
            model_file=str(folder / "sentencepiece.model"))
        tr = ctranslate2.Translator(str(folder / "model"), device="cpu")
        _cache[key] = (tr, sp)
    return _cache[key]


def _split_sentences(text: str):
    parts = re.split(r"(?<=[.!?。？！\n])\s*", text.strip())
    return [p for p in parts if p.strip()]


def _clean(s: str) -> str:
    # sentencepiece 경계기호(▁) 등 군더더기 정리
    return s.replace("▁", " ").replace("  ", " ").strip()


def _direct(text, src, tgt):
    tr, sp = _load(src, tgt)
    out = []
    for sent in _split_sentences(text):
        tokens = sp.encode(sent, out_type=str)
        res = tr.translate_batch([tokens])
        out.append(sp.decode(res[0].hypotheses[0]))
    return _clean(" ".join(out))


def translate(text: str, src: str, tgt: str) -> str:
    if not text.strip() or src == tgt:
        return text
    if (src, tgt) in _PACK_DIRS:
        return _direct(text, src, tgt)
    # 영어를 경유 (예: 한→일 = 한→영→일)
    if (src, "en") in _PACK_DIRS and ("en", tgt) in _PACK_DIRS:
        return _direct(_direct(text, src, "en"), "en", tgt)
    raise ValueError(f"{LANGS.get(src, src)}→{LANGS.get(tgt, tgt)} 번역 언어팩이 없어요.")


def detect_lang(text: str) -> str:
    """글의 언어를 대략 추정합니다."""
    if re.search(r"[가-힣]", text):
        return "ko"
    if re.search(r"[ぁ-んァ-ン]", text):   # 일본어 가나
        return "ja"
    if re.search(r"[一-鿿]", text):          # 한자(가나·한글 없으면 중국어로 봄)
        return "zh"
    return "en"


def translate_to(text: str, tgt: str) -> tuple[str, str]:
    """출발어는 자동 추정, 도착어(tgt)로 번역. 반환: (방향설명, 결과)"""
    src = detect_lang(text)
    if src == tgt:
        src = "en" if tgt != "en" else "ko"   # 같으면 반대로 살짝 보정
    result = translate(text, src, tgt)
    return f"{LANGS.get(src, src)} → {LANGS.get(tgt, tgt)}", result
