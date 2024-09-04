# Makefile to download and set up models

## CUDA
CUDA_VERSION := "12.2"

# Define directories
MODEL_DIR := models
INSIGHTFACE_DIR := $(MODEL_DIR)/.insightface/models/buffalo_l

# Define URLs curl -L -o /app/models/GFPGANv1.4.pth https://huggingface.co/hacksider/deep-live-cam/resolve/main/GFPGANv1.4.pth

GFPGAN_URL := https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/GFPGANv1.4.pth
INSWAPPER_URL := https://github.com/facefusion/facefusion-assets/releases/download/models-3.0.0/inswapper_128_fp16.onnx
BUFFALO_L_URL := https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip
W600K_R50_URL := https://huggingface.co/maze/faceX/resolve/e010b5098c3685fd00b22dd2aec6f37320e3d850/w600k_r50.onnx
GENDER_AGE_URL := https://huggingface.co/DIAMONIK7777/antelopev2/resolve/main/genderage.onnx
PARSING_PARSET_URL := https://huggingface.co/gmk123/GFPGAN/resolve/main/parsing_parsenet.pth
DETECTION_RESNET_URL := https://huggingface.co/sinadi/aar/resolve/main/detection_Resnet50_Final.pth

# Targets
.PHONY: clean clean-all init all setup_models run

all: init setup_models
re: clean init setup_models run
init: 
	mkdir -p models
	
run: 
	docker compose run Deep-Live-Cam

clean: owner
	rm -rf models model-pool
clean-all: clean
	echo "WARNING: This will purge the output files generated in the output folder! Purge in 2s"
	sleep 2
	rm -rf output/output_files/*
	rm -rf output/enhanced/*

setup_models: owner clean
	git clone https://huggingface.co/AVGRadmin/model-pool
	mkdir -p models
	mv model-pool/models/* models/
	rm -rf model-pool
build:
	docker build -t Deep-Swap-Docker:latest ./docker/Dockerfile.$(CUDA_VERSION)

owner:
	sudo chown -R $(USER) .
