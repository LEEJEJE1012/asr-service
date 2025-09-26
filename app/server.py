# app/server.py
import time
import logging
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.services.asr_fw import FasterWhisperASR
from app.services.asr_ow import OpenAIWhisperASR

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
