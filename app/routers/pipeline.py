# app/routers/pipeline.py
from __future__ import annotations

import base64
import time
from functools import lru_cache
from typing import Optional, Literal

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request

from app.core.config import settings
from app.schemas.pipeline import (
    PipelineResponse,
    STTResult, SearchResult, SearchItem, TTSResult,
)
from app.services.audio_io import to_f32_16k_mono, seconds_from_f32_16k
from app.services.policy_search import PolicySearch
from app.services.edge_tts import synthesize_mp3

router = APIRouter(tags=["pipeline"])

# --------------------------------------------------------------------
# Lazy singletons
# --------------------------------------------------------------------
@lru_cache(maxsize=1)
def _policy() -> PolicySearch:
    # settings에서 csv/qdrant/embed_model 설정을 읽어 초기화(영속 인덱스)
    return PolicySearch()

# 간단 요약기 (Top-1 support 문장의 앞 1~2개를 사용)
def _simple_summary(text: str, max_chars: int = 180) -> str:
    t = (text or "").strip()
    if not t:
        return "요약 정보를 찾지 못했습니다."
    # 문장 단위 분리(간단)
    # 한국어 마침표/문장 경계가 복잡하지만 우선 '.' 기준 + 안전 자르기
    parts = [p.strip() for p in t.replace("..", ".").split(".") if p.strip()]
    summary = ". ".join(parts[:2]).strip()
    if summary and not summary.endswith("."):
        summary += "."
    if len(summary) > max_chars:
        summary = summary[: max_chars - 1] + "…"
    return summary or "요약 정보를 찾지 못했습니다."

# --------------------------------------------------------------------
# End-to-end pipeline
# --------------------------------------------------------------------
@router.post("/stt_search_tts", response_model=PipelineResponse)
async def stt_search_tts(
    request: Request,
    audio: UploadFile = File(...),
    engine: Literal["fw", "ow"] = Form(settings.ENGINE_DEFAULT),
    language: Optional[str] = Form(None),
    beam_size: Optional[int] = Form(None),
    topk: Optional[int] = Form(None),
    voice: Optional[str] = Form(None),
):
    """
    Audio → STT → Vector Search(Top-K) → Summary(Top-1) → Edge TTS(MP3)
    """
    raw = await audio.read()

    # 1) 디코드 & 길이 제한
    wav = to_f32_16k_mono(raw)
    audio_sec = seconds_from_f32_16k(wav)
    if audio_sec > settings.MAX_AUDIO_SEC:
        raise HTTPException(status_code=413, detail=f"Audio too long (> {settings.MAX_AUDIO_SEC}s)")

    # 2) STT (서버 싱글톤 재사용)
    t0 = time.time()
    lang = language or settings.LANGUAGE
    if engine == "ow":
        text, meta = request.app.state.OW.transcribe(wav, language=lang)
    else:
        if beam_size:
            request.app.state.FW.beam_size = int(beam_size)
        text, meta = request.app.state.FW.transcribe(wav, language=lang)
    decode_s = round(time.time() - t0, 3)

    stt = STTResult(
        text=text,
        engine=engine,
        decode_s=decode_s,
        audio_sec=audio_sec,
    )

    # 3) 검색
    k = topk or settings.TOPK_DEFAULT
    pol = _policy()
    results_dicts = pol.search(text, topk=k)
    items = [SearchItem(**r) for r in results_dicts]
    search = SearchResult(query=text, topk=k, results=items)

    # 4) 요약 (Top-1의 support 기준)
    summary = _simple_summary(items[0].support if items else "")

    # 5) Edge TTS 합성 (MP3)
    v = voice or settings.TTS_VOICE_DEFAULT
    mp3_bytes = await synthesize_mp3(summary, voice=v)
    mp3_b64 = base64.b64encode(mp3_bytes).decode("ascii")
    # 대략적 길이 추정(문자수 기반; UI 힌트용)
    dur_est = max(1.5, len(summary) / 8.0)

    tts = TTSResult(
        voice=v,
        mp3_b64=mp3_b64,
        duration_est_s=round(dur_est, 2),
    )

    return PipelineResponse(
        stt=stt,
        search=search,
        summary=summary,
        tts=tts,
    )
