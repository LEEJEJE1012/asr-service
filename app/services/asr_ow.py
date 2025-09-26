from typing import Tuple, Dict, Any, Optional
import os
import numpy as np
import whisper  # openai-whisper

from app.core.config import settings
from .audio_io import to_f32_16k_mono

class OpenAIWhisperASR:
    """
    Unified OW wrapper to match FW interface.
      - transcribe(wav: np.ndarray) -> (text, info)
      - transcribe_bytes(raw: bytes) -> (text, info)

    info = {"duration": None, "language": str}
    """

    def __init__(
        self,
        model_dir: Optional[str] = None,
        model_size: str = "medium",
        device: Optional[str] = None,
    ):
        self.model_dir = model_dir or settings.OW_MODEL_DIR
        self.device = device or settings.FW_DEVICE  # whisper.load_model의 device 파라미터에 전달
        # 로컬 모델 경로 지원(있으면 우선), 없으면 사이즈명으로 다운로드
        model_id = self.model_dir if (os.path.isdir(self.model_dir) and os.listdir(self.model_dir)) else model_size

        self.model = whisper.load_model(
            model_id,
            device=self.device,
            download_root=os.path.dirname(self.model_dir),
        )

    def transcribe(self, wav: np.ndarray, language: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        if wav.dtype != np.float32:
            wav = wav.astype(np.float32, copy=False)
        lang = language or settings.LANGUAGE

        # GPU일 때 fp16 사용이 기본적으로 유리
        fp16 = (self.device == "cuda")
        result = self.model.transcribe(wav, language=lang, fp16=fp16)
        text = (result.get("text") or "").strip()
        meta = {
            "duration": None,  # openai-whisper는 별도 duration 제공 안 함
            "language": result.get("language", lang) or lang,
        }
        return text, meta

    def transcribe_bytes(self, audio_bytes: bytes, language: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        wav = to_f32_16k_mono(audio_bytes)
        return self.transcribe(wav, language=language)
