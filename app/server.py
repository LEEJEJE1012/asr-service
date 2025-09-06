import time
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.services.asr_fw import FasterWhisperASR
from app.services.asr_ow import OpenAIWhisperASR

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS != ["*"] else ["*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

FW = FasterWhisperASR(settings.FW_MODEL_DIR, compute_type="float16", beam_size=settings.FW_BEAM)
OW = OpenAIWhisperASR(settings.OW_MODEL_DIR)

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...),
                     engine: str = Form(settings.ENGINE_DEFAULT),
                     language: str = Form(settings.LANGUAGE),
                     beam_size: int = Form(settings.FW_BEAM)):
    data = await audio.read()
    t0 = time.time()
    if engine == "fw":
        FW.beam_size = beam_size
        text, dur = FW.transcribe_bytes(data, language=language)
    else:
        text, dur = OW.transcribe_bytes(data, language=language)
    return JSONResponse({"text": text, "decode_s": time.time()-t0, "engine": engine, "audio_sec": dur})
