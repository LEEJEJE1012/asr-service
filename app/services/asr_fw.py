import os
from typing import Tuple, Dict, Any, Optional
import numpy as np
from faster_whisper import WhisperModel

from app.core.config import settings
from .audio_io import to_f32_16k_mono

class FasterWhisperASR:
    """
    Unified FW wrapper:
      - transcribe(wav: np.ndarray) -> (text, info)
      - transcribe_bytes(raw: bytes) -> (text, info)

    info = {"duration": float, "language": str}
    """

    def __init__(
        self,
        model_dir: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
        beam_size: Optional[int] = None,
    ):
        self.model_dir = model_dir or settings.FW_MODEL_DIR
        self.device = device or settings.FW_DEVICE           # "cuda" | "cpu"
        self.compute_type = compute_type or settings.FW_COMPUTE  # "float16" | "int8_float16" | "float32"
        self.beam_size = beam_size or settings.FW_BEAM

        # 로컬 디렉토리에 모델이 있으면 그 경로를, 아니면 "large-v3"를 사용
        model_id = self.model_dir if (os.path.isdir(self.model_dir) and os.listdir(self.model_dir)) else "large-v3"

        self.model = WhisperModel(
            model_id,
            device=self.device,
            compute_type=self.compute_type,
            download_root=os.path.dirname(self.model_dir),
        )

    def transcribe(self, wav: np.ndarray, language: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """Input: float32 mono PCM @16kHz"""
        if wav.dtype != np.float32:
            wav = wav.astype(np.float32, copy=False)
        lang = language or settings.LANGUAGE

        segments, info = self.model.transcribe(
            wav,
            language=lang,
            beam_size=self.beam_size,
            vad_filter=False,
        )
        text = "".join(s.text for s in segments).strip()
        meta = {
            "duration": float(getattr(info, "duration", 0.0) or 0.0),
            "language": getattr(info, "language", lang) or lang,
        }
        return text, meta

    def transcribe_bytes(self, audio_bytes: bytes, language: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        wav = to_f32_16k_mono(audio_bytes)
        return self.transcribe(wav, language=language)
