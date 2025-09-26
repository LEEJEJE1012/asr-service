import os
from dotenv import load_dotenv

load_dotenv()



# class Settings:
#     HOST = os.getenv("ASR_HOST", "0.0.0.0")
#     PORT = int(os.getenv("ASR_PORT", 8000))
#     CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS","*").split(",")]
#     ENGINE_DEFAULT = os.getenv("ASR_ENGINE_DEFAULT","fw")
#     LANGUAGE = os.getenv("ASR_LANGUAGE","ko")
#     FW_BEAM = int(os.getenv("ASR_FW_BEAM","1"))
#     MAX_AUDIO_SEC = int(os.getenv("ASR_MAX_AUDIO_SEC","15"))

#     BASE_DIR = os.getenv("ASR_BASE_DIR","/root/asr-service")
#     UPLOAD_DIR = os.getenv("ASR_UPLOAD_DIR", f"{BASE_DIR}/data/uploads")
#     LOG_DIR = os.getenv("ASR_LOG_DIR", f"{BASE_DIR}/logs")
#     MODEL_DIR = os.getenv("ASR_MODEL_DIR", f"{BASE_DIR}/models")
#     FW_MODEL_DIR = os.getenv("FW_MODEL_DIR", f"{MODEL_DIR}/faster-whisper/large-v3")
#     OW_MODEL_DIR = os.getenv("OW_MODEL_DIR", f"{MODEL_DIR}/whisper/medium")

# settings = Settings()

class Settings:
    # ---- Server / API ----
    HOST = os.getenv("ASR_HOST", "0.0.0.0")
    PORT = int(os.getenv("ASR_PORT", "8000"))
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]
    ENGINE_DEFAULT = os.getenv("ASR_ENGINE_DEFAULT", "fw")
    LANGUAGE = os.getenv("ASR_LANGUAGE", "ko")
    FW_BEAM = int(os.getenv("ASR_FW_BEAM", "1"))
    MAX_AUDIO_SEC = int(os.getenv("ASR_MAX_AUDIO_SEC", "15"))

    # ---- Paths (기존 경로 체계 유지) ----
    BASE_DIR = os.getenv("ASR_BASE_DIR", "/root/asr-service")
    UPLOAD_DIR = os.getenv("ASR_UPLOAD_DIR", f"{BASE_DIR}/data/uploads")
    LOG_DIR = os.getenv("ASR_LOG_DIR", f"{BASE_DIR}/logs")
    MODEL_DIR = os.getenv("ASR_MODEL_DIR", f"{BASE_DIR}/models")
    FW_MODEL_DIR = os.getenv("FW_MODEL_DIR", f"{MODEL_DIR}/faster-whisper/large-v3")
    OW_MODEL_DIR = os.getenv("OW_MODEL_DIR", f"{MODEL_DIR}/whisper/medium")

    # ---- FW 실행 옵션 (신규) ----
    FW_DEVICE = os.getenv("FW_DEVICE", "cuda")          # "cuda" | "cpu"
    FW_COMPUTE = os.getenv("FW_COMPUTE", "float16")     # "float32" | "float16" | "int8_float16"

    # ---- Policy Search (신규) ----
    POLICY_CSV_PATH = os.getenv("POLICY_CSV_PATH", f"{BASE_DIR}/data/csv/gov24_services_with_tags.csv")
    QDRANT_PATH = os.getenv("QDRANT_PATH", f"{BASE_DIR}/qdrant_db")
    EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
    TOPK_DEFAULT = int(os.getenv("TOPK_DEFAULT", "3"))

    # ---- TTS (신규) ----
    TTS_VOICE_DEFAULT = os.getenv("TTS_VOICE_DEFAULT", "ko-KR-SunHiNeural")

    @classmethod
    def ensure_dirs(cls):
        """필요 디렉토리 생성 (없으면 생성)"""
        dirs = [
            cls.UPLOAD_DIR,
            cls.LOG_DIR,
            cls.MODEL_DIR,
            os.path.dirname(cls.FW_MODEL_DIR),
            os.path.dirname(cls.OW_MODEL_DIR),
            cls.QDRANT_PATH,
            os.path.dirname(cls.POLICY_CSV_PATH),
        ]
        for d in dirs:
            if d and not os.path.exists(d):
                os.makedirs(d, exist_ok=True)

    @classmethod
    def as_dict(cls):
        """상수만 dict로 확인용"""
        return {k: getattr(cls, k) for k in dir(cls) if k.isupper()}

settings = Settings()
Settings.ensure_dirs()