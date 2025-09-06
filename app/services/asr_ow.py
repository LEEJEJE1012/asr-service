import os, whisper
from .audio_io import to_f32_16k_mono

class OpenAIWhisperASR:
    def __init__(self, model_dir: str):
        self.model = whisper.load_model("medium", download_root=os.path.dirname(model_dir))

    def transcribe_bytes(self, audio_bytes: bytes, language="ko"):
        wav = to_f32_16k_mono(audio_bytes)
        res = self.model.transcribe(wav, language=language, fp16=True, without_timestamps=True)
        return res["text"], None
