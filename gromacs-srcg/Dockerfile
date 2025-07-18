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
RUN pip install python-dotenv boto3 salad-cloud-sdk

WORKDIR /app

COPY main_basic.py helper.py main_salad.py salad_monitor.py /app/
COPY systems /app/systems

CMD ["python", "main_salad.py"]


# 6 prebuilt GROMACS tpr files for benchmarking and test
#    488 -rw-r--r-- 1 ubuntu ubuntu    495880 Aug 15 15:14 1.tpr
#    968 -rw-r--r-- 1 ubuntu ubuntu    991196 Aug 15 15:15 2.tpr
#   3972 -rw-r--r-- 1 ubuntu ubuntu   4065500 Aug 15 15:15 3.tpr
#   6260 -rw-r--r-- 1 ubuntu ubuntu   6406152 Aug 15 15:15 4.tpr
#  28108 -rw-r--r-- 1 ubuntu ubuntu  28781724 Aug 15 15:15 5.tpr
# 132224 -rw-r--r-- 1 ubuntu ubuntu 135391332 Aug 15 15:15 6.tpr

# You can download and uncompress 6 models, change their filenames and then put the 6 tpr files  in the ./systems folder
# https://hpc.fau.de/files/2022/02/r-143a-in-hexane-nhr-fau.zip
# https://hpc.fau.de/files/2022/02/rnanvt-nhr-fau.zip
# https://hpc.fau.de/files/2022/02/membrane-protein-rrze-nhr-fau.zip
# https://hpc.fau.de/files/2022/02/protein-explicit-water-nhr-fau.zip
# https://github.com/PDC-support/benchmarks-procurement/blob/master/benchmarks/GROMACS/EAG1-channel_strong-scaling/inputs/topol.tpr.gz
# https://zenodo.org/records/3893789/files/GROMACS_heterogeneous_parallelization_benchmark_info_and_systems_JCP.tar.gz?download=1
