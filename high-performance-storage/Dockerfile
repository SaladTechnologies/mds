# For your project, select a base image with GPU support from PyTorch or Nvidia
# https://hub.docker.com/r/nvidia/cuda/tags
# https://hub.docker.com/r/pytorch/pytorch

#FROM python:3.10-slim
FROM docker.io/pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime

WORKDIR /app

RUN apt-get update && apt-get install -y \
    wget \
    tree \
    nano \
    curl \
    && rm -rf /var/lib/apt/lists/*


RUN pip install speedtest-cli
RUN pip install pythonping
RUN pip install python-dotenv

# https://rclone.org/downloads/
COPY rclone-v1.68.2-linux-amd64.deb /app
RUN dpkg -i rclone-v1.68.2-linux-amd64.deb

RUN mkdir -p /root/.config/rclone
COPY benchmark.py config.py ./

CMD ["python", "benchmark.py"]