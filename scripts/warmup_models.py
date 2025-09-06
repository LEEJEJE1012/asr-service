import os, time
from app.core.config import settings
from app.services.asr_fw import FasterWhisperASR
from app.services.asr_ow import OpenAIWhisperASR

os.makedirs(settings.FW_MODEL_DIR, exist_ok=True)
os.makedirs(settings.OW_MODEL_DIR, exist_ok=True)

t0=time.time(); FasterWhisperASR(settings.FW_MODEL_DIR); t1=time.time()
OpenAIWhisperASR(settings.OW_MODEL_DIR); t2=time.time()
print(f"FW ready in {t1-t0:.1f}s, OW ready in {t2-t1:.1f}s")
