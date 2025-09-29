# app/schemas/pipeline.py
from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# -----------------------------
# STT
# -----------------------------
class STTResult(BaseModel):
    """Result of speech-to-text decoding."""
    text: str = Field(..., description="Transcribed text.")
    engine: Literal["fw", "ow"] = Field(..., description="ASR engine used: fw(Faster-Whisper) or ow(OpenAI Whisper).")
    decode_s: float = Field(..., ge=0.0, description="Wall-clock decoding time in seconds.")
    audio_sec: Optional[float] = Field(None, ge=0.0, description="Duration of input audio in seconds (if available).")


# -----------------------------
# Search (vector retrieval on policies)
# -----------------------------
class SearchItem(BaseModel):
    """One retrieved policy item."""
    rank: int = Field(..., ge=1, description="1-based rank after (re)ranking.")
    service_id: str = Field("", description="Service ID (if available).")
    service_name: str = Field("", description="Human-readable policy/service name.")
    score: float = Field(..., description="Similarity score from vector search (larger means more similar).")
    tags: List[str] = Field(default_factory=list, description="Comma-split tags.")
    support: str = Field("", description="Support/benefit description.")
    url: Optional[str] = Field(None, description="Source / details URL (if available).")
    
    # 추가된 모든 CSV 필드들
    application_deadline: str = Field("", description="신청기한")
    contact: str = Field("", description="문의처")
    application_method: str = Field("", description="신청방법")
    receiving_agency: str = Field("", description="접수기관명")
    support_type: str = Field("", description="지원유형")
    target_beneficiaries: str = Field("", description="지원대상")
    selection_criteria: str = Field("", description="선정기준")
    required_documents: str = Field("", description="구비서류")


class SearchResult(BaseModel):
    """Top-K retrieval result for a given query text."""
    query: str = Field(..., description="Query text (typically STT output).")
    topk: int = Field(..., ge=1, description="Requested number of results.")
    results: List[SearchItem] = Field(default_factory=list, description="Ranked retrieval results.")


# -----------------------------
# TTS (Edge TTS)
# -----------------------------
class TTSRequest(BaseModel):
    """TTS synthesis request."""
    text: str = Field(..., description="Text to synthesize into speech.")
    voice: str = Field("ko-KR-SunHiNeural", description="Voice name for synthesis.")
    rate: Optional[str] = Field(default=None, description="Speech rate (e.g., '+10%', '-5%').")
    volume: Optional[str] = Field(default=None, description="Speech volume (e.g., '+0%', '+3dB').")
    pitch: Optional[str] = Field(default=None, description="Speech pitch (e.g., '+0Hz', '+2st').")

class TTSResult(BaseModel):
    """Edge TTS synthesis result."""
    voice: str = Field(..., description="Voice name used for synthesis (e.g., 'ko-KR-SunHiNeural').")
    mp3_b64: str = Field(..., description="Base64-encoded MP3 bytes of the synthesized speech.")
    duration_est_s: float = Field(..., ge=0.0, description="Estimated playback duration in seconds.")


# -----------------------------
# Pipeline aggregate
# -----------------------------
class PipelineResponse(BaseModel):
    """
    Unified response for the end-to-end pipeline:

      Audio → STT → Vector Search (Top-K policies) → Summary(Top-1) → Edge TTS(MP3)
    """
    stt: STTResult
    search: SearchResult
    summary: str = Field(..., description="Short summary text derived from the top-1 policy.")
    tts: TTSResult
