import os
import uuid
from typing import Optional
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import FileResponse

import torch
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
import torchaudio

# --- 설정 변수 ---
TTS_OUTPUT_DIR = "./tts_out"

# --- 애플리케이션 시작 ---
app = FastAPI(title="FastSpeech TTS Service")

@app.on_event("startup")
def startup_event():
    # 서버 시작 시 출력 폴더가 없으면 생성합니다.
    if not os.path.exists(TTS_OUTPUT_DIR):
        os.makedirs(TTS_OUTPUT_DIR)
        print(f"'{TTS_OUTPUT_DIR}' 디렉토리를 생성했습니다.")

# FastSpeech 모델을 한 번만 로드하도록 캐싱합니다.
@lru_cache(maxsize=1)
def get_tts_components():
    print("FastSpeech 모델 컴포넌트를 로드하는 중입니다. (이 과정은 시간이 걸릴 수 있습니다.)")
    try:
        processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
        model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts")
        vocoder = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan")
        
        # 스피커 임베딩 로드 또는 생성
        # 실제 사용 시에는 특정 오디오 파일에서 임베딩을 추출하는 로직이 필요합니다.
        # 예시: speaker_embeddings = extract_speaker_embeddings("path_to_speaker_audio.wav")
        speaker_embeddings = torch.randn((1, 512))
        
        print("FastSpeech 모델 로딩 완료.")
        return processor, model, vocoder, speaker_embeddings
    except Exception as e:
        print(f"오류: FastSpeech 모델 로드 실패 - {e}")
        return None, None, None, None

# --- Pydantic 모델 ---
class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "default"

# --- API 엔드포인트 ---
@app.post("/tts")
async def tts(req: TTSRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    
    processor, model, vocoder, speaker_embeddings = get_tts_components()
    if model is None:
        raise HTTPException(status_code=503, detail="TTS 서비스가 준비되지 않았습니다. 모델 로드 실패.")
    
    try:
        fname = f"tts_{uuid.uuid4().hex[:8]}.wav"
        out_path = os.path.join(TTS_OUTPUT_DIR, fname)
        
        # 텍스트를 모델 입력 형식으로 변환
        inputs = processor(text=req.text.strip(), return_tensors="pt")

        # 음성 합성
        with torch.no_grad():
            speech = model.generate_speech(
                inputs["input_ids"],
                speaker_embeddings=speaker_embeddings,
                vocoder=vocoder
            )

        # 생성된 음성 저장
        torchaudio.save(out_path, speech.unsqueeze(0), 16000)
        
        return {"file": out_path, "voice": req.voice}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"음성 합성 중 오류 발생: {str(e)}")

@app.get("/tts/file")
async def tts_file(path: str):
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="file not found")
    
    return FileResponse(path, media_type="audio/wav", filename=os.path.basename(path))