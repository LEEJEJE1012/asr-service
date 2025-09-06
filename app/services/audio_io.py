import numpy as np, ffmpeg

TARGET_SR = 16000

def to_f32_16k_mono(raw: bytes) -> np.ndarray:
    out, _ = (
        ffmpeg.input('pipe:0')
              .output('pipe:1', format='f32le', acodec='pcm_f32le', ac=1, ar=str(TARGET_SR))
              .run(input=raw, capture_stdout=True, capture_stderr=True)
    )
    return np.frombuffer(out, dtype=np.float32)
