# app/server.py
import time
import logging
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.services.asr_fw import FasterWhisperASR
from app.services.asr_ow import OpenAIWhisperASR
from app.services.edge_tts import synthesize_mp3
from app.schemas.pipeline import TTSRequest, TTSResult

# 로깅 설정 (가장 먼저)
try:
    import logging_config  # 프로젝트 루트의 로깅 초기화 모듈
except ImportError:
    # logging_config가 없으면 기본 로깅 설정
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 라우터
from app.routers.pipeline import router as pipeline_router

# ------------------------------------------------------------------------------
# FastAPI app
# ------------------------------------------------------------------------------
app = FastAPI(title="ASR Service", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------------------
# Singleton ASR instances (재활용)
# ------------------------------------------------------------------------------
FW = FasterWhisperASR(
    model_dir=settings.FW_MODEL_DIR,
    device=settings.FW_DEVICE,
    compute_type=settings.FW_COMPUTE,   # 기존엔 "float32" 고정이었으나 설정 반영
    beam_size=settings.FW_BEAM,
)
OW = OpenAIWhisperASR(
    model_dir=settings.OW_MODEL_DIR,
    device=settings.FW_DEVICE,          # whisper.load_model에 전달
)

# FastAPI 앱 state에 등록 → 라우터에서 request.app.state로 접근
app.state.FW = FW
app.state.OW = OW

# ------------------------------------------------------------------------------
# Routers
# ------------------------------------------------------------------------------
# 엔드투엔드 파이프라인: /stt_search_tts
app.include_router(pipeline_router, prefix="")

# ------------------------------------------------------------------------------
# Basic endpoints
# ------------------------------------------------------------------------------
@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    engine: str = Form(settings.ENGINE_DEFAULT),
    language: str = Form(settings.LANGUAGE),
    beam_size: int = Form(settings.FW_BEAM),
):
    data = await audio.read()
    t0 = time.time()

    if engine == "fw":
        app.state.FW.beam_size = beam_size
        text, meta = app.state.FW.transcribe_bytes(data, language=language)
        duration = meta.get("duration")
    else:
        text, meta = app.state.OW.transcribe_bytes(data, language=language)
        duration = meta.get("duration")

    return JSONResponse(
        {
            "text": text,
            "decode_s": round(time.time() - t0, 3),
            "engine": engine,
            "audio_sec": duration,
        }
    )

@app.post("/synthesize", response_model=TTSResult)
async def synthesize(request: TTSRequest):
    """
    텍스트를 받아서 Edge TTS로 음성을 합성합니다.
    
    Parameters:
    - text: 합성할 텍스트
    - voice: 음성 선택 (기본: ko-KR-SunHiNeural)
    - rate: 말하기 속도 (예: "+10%", "-5%")
    - volume: 음량 (예: "+0%", "+3dB")
    - pitch: 음조 (예: "+0Hz", "+2st")
    """
    import base64
    
    # Edge TTS로 음성 합성
    mp3_bytes = await synthesize_mp3(
        text=request.text,
        voice=request.voice,
        rate=request.rate if request.rate else None,
        volume=request.volume if request.volume else None,
        pitch=request.pitch if request.pitch else None
    )
    
    # Base64 인코딩
    mp3_b64 = base64.b64encode(mp3_bytes).decode("ascii")
    
    # 대략적 길이 추정 (문자수 기반)
    duration_est = max(1.5, len(request.text) / 8.0)
    
    return TTSResult(
        voice=request.voice,
        mp3_b64=mp3_b64,
        duration_est_s=round(duration_est, 2)
    )
