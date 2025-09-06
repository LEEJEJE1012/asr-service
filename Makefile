PYTHONPATH ?= /root/asr-service

.PHONY: install warmup run

install:
	pip install --upgrade pip wheel setuptools
	# CUDA 12.4 용 Torch (필요 시 cu121로 변경)
	pip install --index-url https://download.pytorch.org/whl/cu124 torch torchaudio
	pip install -r requirements.txt
	apt-get update && apt-get install -y ffmpeg

warmup:
	PYTHONPATH=$(PYTHONPATH) python scripts/warmup_models.py

run:
	bash scripts/run_uvicorn.sh
