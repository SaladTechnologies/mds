# For your project, select a base image with GPU support from PyTorch or Nvidia
# https://hub.docker.com/r/nvidia/cuda/tags
# https://hub.docker.com/r/pytorch/pytorch
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    wget \
    tree \
    && rm -rf /var/lib/apt/lists/*

RUN pip install boto3
RUN pip install python-dotenv

RUN mkdir -p /app/data

# Copy your code and data
# the check.py is only for debugging
COPY main.py config.py check.py ./

# It retreives a job, downloads its input, runs simulation, saves the state regularly and upload the final output.
CMD ["python","main.py"]