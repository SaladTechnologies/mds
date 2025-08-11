# Select a base image: https://hub.docker.com/r/continuumio/miniconda3
FROM continuumio/miniconda3:25.1.1-0 

RUN apt-get update && apt-get install -y curl net-tools iputils-ping 

# Optional: Install VS Code Server for remote debugging
# https://docs.salad.com/tutorials/vscode-remote-development#interactive-mode
# Log in the instance using the terminal, and then run the following commands:
# code tunnel user login --provider github
# nohup code tunnel --accept-server-license-terms --name XXX &> output.log &
RUN curl -Lk 'https://code.visualstudio.com/sha/download?build=stable&os=cli-alpine-x64' -o vscode_cli.tar.gz && \
    tar -xf vscode_cli.tar.gz && \
    mv code /usr/local/bin/code && \
    rm vscode_cli.tar.gz

# Install GROMACS 2024.5，with CUDA and without MPI
# https://anaconda.org/conda-forge/gromacs
# No GPU when building the image, so we use CONDA_OVERRIDE_CUDA to simulate CUDA during build
RUN CONDA_OVERRIDE_CUDA="11.8" conda install -c conda-forge gromacs=2024.5=nompi_cuda_h5cb645a_0 -y

RUN pip install --upgrade pip
RUN pip install python-dotenv boto3

# Install the Kelpie worker (executable)   
RUN wget https://github.com/SaladTechnologies/kelpie/releases/download/0.6.0/kelpie -O /kelpie && chmod +x /kelpie

WORKDIR /app
COPY helper.py main.py /app/

# Run the Kelpie worker
CMD ["/kelpie"]

# The pre-built image:
# docker.io/saladtechnologies/mds:001-gromacs-kelpie-no-sync 


