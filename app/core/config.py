import os
from dotenv import load_dotenv
load_dotenv()

class Settings:
    HOST = os.getenv("ASR_HOST", "0.0.0.0")
    PORT = int(os.getenv("ASR_PORT", 8000))
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS","*").split(",")]
    ENGINE_DEFAULT = os.getenv("ASR_ENGINE_DEFAULT","fw")
    LANGUAGE = os.getenv("ASR_LANGUAGE","ko")
    FW_BEAM = int(os.getenv("ASR_FW_BEAM","1"))
    MAX_AUDIO_SEC = int(os.getenv("ASR_MAX_AUDIO_SEC","15"))

    BASE_DIR = os.getenv("ASR_BASE_DIR","/root/asr-service")
    UPLOAD_DIR = os.getenv("ASR_UPLOAD_DIR", f"{BASE_DIR}/data/uploads")
    LOG_DIR = os.getenv("ASR_LOG_DIR", f"{BASE_DIR}/logs")
    MODEL_DIR = os.getenv("ASR_MODEL_DIR", f"{BASE_DIR}/models")
    FW_MODEL_DIR = os.getenv("FW_MODEL_DIR", f"{MODEL_DIR}/faster-whisper/large-v3")
    OW_MODEL_DIR = os.getenv("OW_MODEL_DIR", f"{MODEL_DIR}/whisper/medium")

settings = Settings()
