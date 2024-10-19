### Introduction

The gromacs_test.py is run when the container starts:

(1)Gather the environment info, include GPU, CPU and software versions.

(2)Run the 'gmx mdrun' command to conduct the test using 6 models and print the results.

(3)Send the result to Salad's job recording System (AWS DynamoDB).

(4)Exit.

When you run the image locally, the container stops when the code finishes executing. On SaladCloud, however, a new node will be allocated to run the image again once the code exits.

By keeping a container group with a few replicas running for some time on SaladCloud, we are able to gather test data from thousands of Salad nodes.

You cannot run this container image on SaladCloud without a job recording system - all test results will be lost !!!

### The blog

After the benchmark test was finished, we downloaded all test data from AWS DynamoDB, and analyzed these data using Pandas on JupyterLab.

We have gathered test data from thousands of Salad nodes, and got enough sameples for each GPU type. The final results were calculated by averaging the data.

https://blog.salad.com/gromacs-benchmark/

### Build and push the container image

docker image build -t docker.io/saladtechnologies/mds:001-gromacs-benchmark -f Dockerfile.gromacs .

docker push docker.io/saladtechnologies/mds:001-gromacs-benchmark

docker rm -f $(docker container ps -aq)

### Local Test with the default settings (CUDA, 200000 steps)

docker run --rm --gpus all -it docker.io/saladtechnologies/mds:001-gromacs-benchmark

docker run --rm --gpus all -it docker.io/saladtechnologies/mds:001-gromacs-benchmark /bin/bash

### Local Test, and send the test result to the job recording System

docker run --rm --gpus all -it \

--env BENCHMARK_ID=$BENCHMARK_ID --env REPORTING_API_URL=$REPORTING_API_URL \

--env REPORTING_AUTH_HEADER=$REPORTING_AUTH_HEADER --env REPORTING_API_KEY=$REPORTING_API_KEY \

docker.io/saladtechnologies/mds:001-gromacs-benchmark


### Deployment on SaladCloud - GPU

Resource Type: 16 vCPU, 8GB RAM, all GPU types

Image Source: docker.io/saladtechnologies/mds:001-gromacs-benchmark 

Replica Count: 10

Environment Variables:

BENCHMARK_ID: ******

REPORTING_API_URL: ******

REPORTING_AUTH_HEADER: ******

REPORTING_API_KEY: ******

NSTEPS: 200000