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
from app.services.edge_tts import synthesize_mp3 as edge_synthesize
from app.services.tts_speecht5 import synthesize_mp3 as speecht5_synthesize

router = APIRouter(tags=["pipeline"])

# --------------------------------------------------------------------
# Lazy singletons
# --------------------------------------------------------------------
@lru_cache(maxsize=1)
def _policy() -> PolicySearch:
    # settings에서 csv/qdrant/embed_model 설정을 읽어 초기화(영속 인덱스)
    return PolicySearch()

# 더 이상 사용하지 않음 - 예전 프로토타입 방식으로 변경

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
    tts_engine: Literal["edge_tts", "speecht5"] = Form("edge_tts"),
):
    """
    Audio → STT → Vector Search(Top-K) → Summary(Top-1) → TTS(MP3)
    
    Parameters:
    - engine: STT 엔진 ("fw" | "ow")
    - language: 언어 코드 (기본: "ko")
    - beam_size: Faster-Whisper beam size (기본: 1)
    - topk: 검색 결과 개수 (기본: 3)
    - voice: TTS 음성 (Edge TTS만 지원)
    - tts_engine: TTS 엔진 ("edge_tts" | "speecht5")
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

    # 4) TTS용 자연스러운 문장 생성 (예전 프로토타입 방식)
    if items:
        service_name = items[0].service_name or "알 수 없는 서비스"
        support_content = items[0].support or "상세 정보가 없습니다"
        spoken_text = f"추천 정책은 {service_name} 입니다. 요약: {support_content}"
    else:
        spoken_text = "적합한 정책을 찾지 못했습니다. 더 구체적으로 말씀해 주세요."

    # 5) TTS 합성 (MP3) - 엔진 선택
    if tts_engine == "edge_tts":
        v = voice or settings.TTS_VOICE_DEFAULT
        mp3_bytes = await edge_synthesize(spoken_text, voice=v)
        tts_voice = v
    else:  # speecht5
        mp3_bytes = speecht5_synthesize(spoken_text)
        tts_voice = "SpeechT5"
    
    mp3_b64 = base64.b64encode(mp3_bytes).decode("ascii")
    # 대략적 길이 추정(문자수 기반; UI 힌트용)
    dur_est = max(1.5, len(spoken_text) / 8.0)

    tts = TTSResult(
        voice=tts_voice,
        mp3_b64=mp3_b64,
        duration_est_s=round(dur_est, 2),
    )

    return PipelineResponse(
        stt=stt,
        search=search,
        summary=spoken_text,
        tts=tts,
    )
