import os
from faster_whisper import WhisperModel
from .audio_io import to_f32_16k_mono

class FasterWhisperASR:
    def __init__(self, model_dir: str, compute_type: str="float16", beam_size:int=1):
        self.model = WhisperModel("large-v3", device="cuda",
                                  compute_type=compute_type,
                                  download_root=os.path.dirname(model_dir))
        self.beam_size = beam_size

    def transcribe_bytes(self, audio_bytes: bytes, language="ko"):
        wav = to_f32_16k_mono(audio_bytes)
        segs, info = self.model.transcribe(wav, language=language,
                                           beam_size=self.beam_size, vad_filter=False)
        text = "".join(s.text for s in segs)
        return text, float(info.duration)
