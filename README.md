This repository provides resources for molecular dynamics simulations and executing long-running tasks on SaladCloud. It includes blogs, reference designs, benchmarking code, demonstration applications, and test reports.

If you are new to SaladCloud, we recommend starting with [the SCE Architectural Overview](https://docs.salad.com/products/sce/getting-started/architectual-overview) and [the Docker Run on SaladCloud](https://docs.salad.com/tutorials/docker-run). The tutorial - [Build High-Performance Applications](https://docs.salad.com/tutorials/high-performance-apps) shares best practices along with proven insights from customers who have successfully built large-scale AI inference applications and run molecular dynamics simulations, using tens to thousands of Salad GPU nodes.

### GROMACS Benchmark

https://github.com/SaladTechnologies/mds/tree/main/gromacs-benchmark

https://blog.salad.com/gromacs-benchmark/

### OpenMM Benchmark

https://github.com/SaladTechnologies/mds/tree/main/openmm-benchmark

https://blog.salad.com/openmm-gpu-benchmark/

### Transcription Benchmark for 1 million hours of YouTube videos

https://docs.salad.com/guides/transcription/sce/youtube

https://blog.salad.com/ai-batch-transcription-benchmark/

### Demo App 1 - Long-running tasks with built-in data management on SaladCloud

Job Queue - Salad Kelpie, Cloud Storage - Cloudflare R2

https://github.com/SaladTechnologies/mds/tree/main/demo-app1

### Demo App 2 (v2) - Long-running tasks with progressive uploads on SaladCloud

Job Queue - AWS SQS, Cloud Storage - Cloudflare R2

https://github.com/SaladTechnologies/mds/tree/main/demo-app2v2

### Inference Server

A simple implementation of inference server on SaladCloud, processing concurrent requests with batched inference. It can be used for image generation, transcription, and non-streaming LLM tasks.

https://github.com/SaladTechnologies/mds/tree/main/inference-server

### High-Performance Storage

Best practices for designing a high-performance storage solution for applications on SaladCloud.

https://github.com/SaladTechnologies/mds/tree/main/high-performance-storage