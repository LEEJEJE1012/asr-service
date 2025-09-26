# app/services/edge_tts.py
from __future__ import annotations

import asyncio
import re
from typing import List, Optional

import edge_tts
from app.core.config import settings

# -----------------------------
# Helpers
# -----------------------------
_SENT_SPLIT = re.compile(r"(?<=[\.!?])|(?<=[다요]\s)")
_WS = re.compile(r"\s+")

def _normalize_text(text: str) -> str:
    return _WS.sub(" ", (text or "").strip())

def _chunk_by_chars(text: str, max_chars: int = 4000) -> List[str]:
    """
    Split text into <= max_chars chunks, preferring sentence boundaries.
    Edge TTS는 4~5k char 이하에서 안정적입니다.
    """
    text = _normalize_text(text)
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    sents = [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]
    chunks: List[str] = []
    buf: List[str] = []
    cur = 0
    for s in sents:
        need = len(s) + (1 if buf else 0)
        if cur + need <= max_chars:
            buf.append(s)
            cur += need
        else:
            if buf:
                chunks.append(" ".join(buf))
            buf = [s]
            cur = len(s)
    if buf:
        chunks.append(" ".join(buf))

    fixed: List[str] = []
    for ch in chunks:
        if len(ch) <= max_chars:
            fixed.append(ch)
        else:
            for i in range(0, len(ch), max_chars):
                fixed.append(ch[i : i + max_chars])
    return [c for c in fixed if c]

# -----------------------------
# Public API
# -----------------------------
async def synthesize_mp3(
    text: str,
    voice: Optional[str] = None,
    rate: Optional[str] = None,    # e.g., "+10%", "-5%"
    volume: Optional[str] = None,  # e.g., "+0%", "+3dB"
    pitch: Optional[str] = None,   # e.g., "+0Hz", "+2st"
    max_chars: int = 4000,
) -> bytes:
    """
    Edge TTS로 MP3 바이트를 합성해 반환합니다 (비동기).
    """
    v = voice or settings.TTS_VOICE_DEFAULT
    
    # Voice 파라미터 검증 및 정리
    if v and isinstance(v, str):
        # "voice=ko-KR-SunHiNeural" 형태의 문자열에서 실제 voice 값만 추출
        if v.startswith("voice="):
            v = v.replace("voice=", "").strip()
        # 공백 제거
        v = v.strip()
    
    # 기본값 설정
    if not v:
        v = "ko-KR-SunHiNeural"
    chunks = _chunk_by_chars(text, max_chars=max_chars)
    if not chunks:
        return b""

    audio = bytearray()
    for ch in chunks:
        # Edge TTS 파라미터 검증 - None 값 제거
        params = {"text": ch, "voice": v}
        if rate and isinstance(rate, str):
            params["rate"] = rate
        if volume and isinstance(volume, str):
            params["volume"] = volume
        if pitch and isinstance(pitch, str):
            params["pitch"] = pitch
        
        comm = edge_tts.Communicate(**params)
        async for msg in comm.stream():
            if msg["type"] == "audio":
                audio += msg["data"]
    return bytes(audio)

async def list_voices(locale_prefix: Optional[str] = None) -> List[dict]:
    """
    사용 가능한 보이스 목록을 반환합니다. (필요시 locale prefix 필터)
    """
    voices = await edge_tts.list_voices()
    if locale_prefix:
        lp = locale_prefix.lower()
        return [v for v in voices if str(v.get("Locale", "")).lower().startswith(lp)]
    return voices

# -----------------------------
# Convenience (동기 래퍼; 테스트/CLI 용)
# -----------------------------
def synthesize_mp3_sync(
    text: str,
    voice: Optional[str] = None,
    rate: Optional[str] = None,
    volume: Optional[str] = None,
    pitch: Optional[str] = None,
    max_chars: int = 4000,
) -> bytes:
    try:
        asyncio.get_running_loop()
        raise RuntimeError("synthesize_mp3_sync는 이벤트 루프 밖에서만 호출하세요.")
    except RuntimeError:
        pass
    return asyncio.run(
        synthesize_mp3(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch, max_chars=max_chars)
    )
