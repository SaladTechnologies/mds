# For your project, select a base image with GPU support from PyTorch or Nvidia
# https://hub.docker.com/r/nvidia/cuda/tags
# https://hub.docker.com/r/pytorch/pytorch

FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    wget \
    tree \
    && rm -rf /var/lib/apt/lists/*

# Install the Kelpie worker (executable)   
RUN wget https://github.com/SaladTechnologies/kelpie/releases/download/0.4.4/kelpie -O /kelpie && chmod +x /kelpie

# Create 3 local folders, which will be accessed by the Kelpie worker
RUN mkdir -p /app/data/input
RUN mkdir -p /app/data/state
RUN mkdir -p /app/data/output

# Copy your code and data
# the check.py is only for debugging
COPY main.py check.py ./

# Run the Kelpie worker
# It retreives a job, run main.py and manage data synchronization
CMD ["/kelpie"]