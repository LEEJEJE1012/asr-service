# app/services/tts_speecht5.py
from __future__ import annotations

import io
import os
import shutil
import subprocess
from functools import lru_cache
from typing import Optional, List

import numpy as np
import torch
import soundfile as sf
from transformers import (
    SpeechT5Processor,
    SpeechT5ForTextToSpeech,
    SpeechT5HifiGan,
)

from app.core.config import settings

# -----------------------------
# Config / device / ffmpeg
# -----------------------------
DEFAULT_SR = 16000

def _pick_device() -> str:
    dev = (settings.FW_DEVICE or "cpu").lower()
    return "cuda" if dev.startswith("cuda") and torch.cuda.is_available() else "cpu"

def _pick_ffmpeg_bin() -> str:
    env_bin = os.getenv("FFMPEG_BIN") or os.getenv("FFMPEG_PATH")
    if env_bin:
        return env_bin
    for c in [
        "/root/miniforge3/envs/server/bin/ffmpeg",
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/opt/homebrew/bin/ffmpeg",
    ]:
        if os.path.exists(c):
            return c
    return shutil.which("ffmpeg") or "ffmpeg"

FFMPEG_BIN = _pick_ffmpeg_bin()

# -----------------------------
# Model loaders (cached)
# -----------------------------
@lru_cache(maxsize=1)
def _load_models(device: str):
    """
    Load SpeechT5 TTS + HiFi-GAN vocoder + processor (cached).
    """
    processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
    model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts")
    vocoder = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan")

    model.to(device).eval()
    vocoder.to(device).eval()
    return processor, model, vocoder

# -----------------------------
# Speaker embedding
# -----------------------------
def _resolve_speaker_embedding(
    emb: Optional[np.ndarray] = None,
    emb_path: Optional[str] = None,
) -> torch.Tensor:
    """
    Return speaker embedding tensor of shape (1, 512).
    Priority: explicit emb -> .npy path -> random.
    """
    if emb is not None:
        arr = np.asarray(emb, dtype=np.float32)
        if arr.ndim == 1:  # (512,)
            arr = arr[None, :]
        assert arr.shape == (1, 512), f"speaker_embedding must be (1,512), got {arr.shape}"
        return torch.from_numpy(arr)

    if emb_path and os.path.exists(emb_path):
        arr = np.load(emb_path).astype(np.float32)
        if arr.ndim == 1:
            arr = arr[None, :]
        assert arr.shape == (1, 512), f"speaker_embedding(.npy) must be (1,512), got {arr.shape}"
        return torch.from_numpy(arr)

    # fallback: random speaker (demo)
    return torch.randn(1, 512, dtype=torch.float32)

# -----------------------------
# Core synthesis
# -----------------------------
def synthesize_wav(
    text: str,
    speaker_embedding: Optional[np.ndarray] = None,
    speaker_embedding_path: Optional[str] = None,
    sample_rate: int = DEFAULT_SR,
) -> bytes:
    """
    SpeechT5 + HiFi-GAN으로 음성을 합성하여 **WAV 바이트**를 반환합니다.
    - text: 입력 문장 (길면 여러 번 호출하여 이어붙이는 방식을 권장)
    - speaker_embedding(_path): (1,512) 임베딩 또는 .npy 파일 (없으면 랜덤)
    - sample_rate: 기본 16000
    """
    if not text or not text.strip():
        return b""

    device = _pick_device()
    processor, model, vocoder = _load_models(device)

    inputs = processor(text=[text], return_tensors="pt")
    spk = _resolve_speaker_embedding(speaker_embedding, speaker_embedding_path)

    with torch.no_grad():
        waveform = model.generate_speech(
            inputs["input_ids"].to(device),
            speaker_embeddings=spk.to(device),
            vocoder=vocoder,
        )

    # waveform: (T,) float32-ish tensor on device
    wav = waveform.detach().cpu().numpy().astype(np.float32)

    # write WAV to bytes
    buf = io.BytesIO()
    sf.write(buf, wav, samplerate=sample_rate, format="WAV")
    return buf.getvalue()

def _wav_to_mp3_bytes(wav_bytes: bytes, bitrate: str = "192k") -> bytes:
    """
    ffmpeg로 WAV 바이트를 MP3 바이트로 변환 (libmp3lame 필요).
    """
    p = subprocess.Popen(
        [FFMPEG_BIN, "-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-f", "mp3", "-b:a", bitrate, "pipe:1"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE
    )
    out, _ = p.communicate(input=wav_bytes)
    if p.returncode != 0 or not out:
        raise RuntimeError("ffmpeg mp3 encode failed (check ffmpeg & libmp3lame).")
    return out

def synthesize_mp3(
    text: str,
    speaker_embedding: Optional[np.ndarray] = None,
    speaker_embedding_path: Optional[str] = None,
    sample_rate: int = DEFAULT_SR,
    bitrate: str = "192k",
) -> bytes:
    """
    SpeechT5 + HiFi-GAN으로 **MP3 바이트**를 반환합니다.
    내부적으로 WAV 생성 후 ffmpeg로 MP3로 변환합니다.
    """
    wav_bytes = synthesize_wav(
        text=text,
        speaker_embedding=speaker_embedding,
        speaker_embedding_path=speaker_embedding_path,
        sample_rate=sample_rate,
    )
    if not wav_bytes:
        return b""
    return _wav_to_mp3_bytes(wav_bytes, bitrate=bitrate)
