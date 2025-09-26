# app/services/audio_io.py
from __future__ import annotations

import os
import shutil
import numpy as np
import ffmpeg

# FastAPI가 없는 환경에서도 동작하도록 선택적 임포트
try:
    from fastapi import HTTPException
    _HAS_FASTAPI = True
except Exception:
    _HAS_FASTAPI = False

# -----------------------------
# Config
# -----------------------------
TARGET_SR = int(os.getenv("AUDIO_TARGET_SR", "16000"))

def _pick_ffmpeg_bin() -> str:
    """
    ffmpeg 실행 바이너리를 합리적으로 탐색한다.
    우선순위: env(FFMPEG_BIN/FFMPEG_PATH) > 몇몇 대표 경로 > PATH 검색.
    """
    env_bin = os.getenv("FFMPEG_BIN") or os.getenv("FFMPEG_PATH")
    if env_bin:
        return env_bin

    candidates = [
        "/root/miniforge3/envs/server/bin/ffmpeg",  # 기존 경로 호환
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/opt/homebrew/bin/ffmpeg",  # macOS(Homebrew)
    ]
    for c in candidates:
        if os.path.exists(c):
            return c

    which = shutil.which("ffmpeg")
    return which or "ffmpeg"

FFMPEG_BIN = _pick_ffmpeg_bin()


# -----------------------------
# Errors
# -----------------------------
def _raise_decode_error(detail: str):
    if _HAS_FASTAPI:
        raise HTTPException(status_code=422, detail=detail)
    raise RuntimeError(detail)


# -----------------------------
# Public API
# -----------------------------
def to_f32_16k_mono(raw: bytes, target_sr: int = TARGET_SR) -> np.ndarray:
    """
    임의의 오디오 바이트(raw)를 ffmpeg로 디코딩하여
    16kHz mono float32(PCM f32le) numpy 배열로 변환한다.
    - 지원 포맷: ffmpeg가 읽을 수 있으면 모두( wav, mp3, m4a, aac, ogg, flac, ... )
    - 실패 시 422/RuntimeError 예외

    Parameters
    ----------
    raw : bytes
        업로드된 오디오 파일의 원시 바이트
    target_sr : int
        목표 샘플레이트(기본 16000)

    Returns
    -------
    np.ndarray
        dtype=float32, shape=(n_samples,)
    """
    try:
        out, err = (
            ffmpeg
            .input("pipe:0")
            .output(
                "pipe:1",
                format="f32le",
                acodec="pcm_f32le",
                ac=1,
                ar=str(int(target_sr)),
            )
            .run(
                input=raw,
                capture_stdout=True,
                capture_stderr=True,
                cmd=FFMPEG_BIN,
            )
        )
    except ffmpeg.Error as e:
        # stderr를 조금 잘라서 힌트 제공
        stderr = e.stderr.decode("utf-8", errors="ignore") if isinstance(e.stderr, (bytes, bytearray)) else str(e.stderr)
        hint = stderr.strip().splitlines()[-5:]
        _raise_decode_error(f"Audio decode failed (ffmpeg). Hint: {' | '.join(hint)}")

    if not out:
        # 디코드 성공이지만 바이트가 비어있는 경우
        tail = (err or b"").decode("utf-8", errors="ignore").strip().splitlines()[-3:]
        _raise_decode_error(f"Audio decode produced empty output. Hint: {' | '.join(tail)}")

    wav = np.frombuffer(out, dtype=np.float32)
    if wav.ndim != 1 or wav.size == 0:
        _raise_decode_error("Decoded PCM is empty or invalid shape.")
    return wav


def seconds_from_f32_16k(wav: np.ndarray, sr: int = TARGET_SR) -> float:
    """
    float32 mono PCM 배열의 길이를 초 단위로 반환.
    """
    if not isinstance(wav, np.ndarray) or wav.dtype != np.float32:
        _raise_decode_error("Input must be a float32 numpy array.")
    if sr <= 0:
        _raise_decode_error("Sample rate must be positive.")
    return round(float(wav.shape[0]) / float(sr), 3)


# -----------------------------
# (선택) 간단한 정규화/클리핑 유틸
# -----------------------------
def safe_clip(wav: np.ndarray, clip_val: float = 1.0) -> np.ndarray:
    """
    [-clip_val, +clip_val]로 안전하게 클리핑.
    모델/후단에 따라 필요 시 사용.
    """
    if not isinstance(wav, np.ndarray) or wav.dtype != np.float32:
        _raise_decode_error("Input must be a float32 numpy array.")
    return np.clip(wav, -float(clip_val), float(clip_val), out=wav.copy())


# -----------------------------
# 모듈 상태 확인용(선택)
# -----------------------------
def ffmpeg_path() -> str:
    """현재 사용 중인 ffmpeg 실행 경로(또는 명령) 반환"""
    return FFMPEG_BIN
