# Python 3.12
FROM continuumio/miniconda3:25.1.1-0 

RUN apt-get update && apt-get install -y curl net-tools iputils-ping python3-pip nginx

# Optional: Install VS Code Server for remote debugging
# https://docs.salad.com/tutorials/vscode-remote-development#interactive-mode
RUN curl -Lk 'https://code.visualstudio.com/sha/download?build=stable&os=cli-alpine-x64' -o vscode_cli.tar.gz && \
    tar -xf vscode_cli.tar.gz && \
    mv code /usr/local/bin/code && \
    rm vscode_cli.tar.gz

# To connect using VS Code:
# Log in the instance using the terminal, and then run the following commands:
# code tunnel user login --provider github
# nohup code tunnel --accept-server-license-terms --name XXX &> output.log &

# http://docs.openmm.org/latest/userguide/application/01_getting_started.html#installing-openmm
RUN conda install -c conda-forge openmm=8.3.0 cuda-version=12.6 -y

RUN pip install python-dotenv boto3 salad-cloud-sdk

WORKDIR /app

COPY main_basic.py helper.py main_salad.py salad_monitor.py /app/

CMD ["python", "main_salad.py"]


# The pre-built image:
# docker.io/saladtechnologies/mds:001-openmm-srcg