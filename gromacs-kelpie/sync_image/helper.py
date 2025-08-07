import os
import time
import boto3
import sys
import json
import glob
import re
import subprocess
import requests
from boto3.s3.transfer import TransferConfig
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
 
load_dotenv()

# Assigned automatically while running on SaladCloud
SALAD_MACHINE_ID =  os.getenv("SALAD_MACHINE_ID", "local")

# Access to the Cloudflare R2 bucket 
AWS_ACCESS_KEY_ID      = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY  = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_ENDPOINT_URL       = os.getenv("AWS_ENDPOINT_URL")
AWS_REGION             = os.getenv("AWS_REGION")

# Task parameters
TASK_CREATION_TIME   = os.getenv("TASK_CREATION_TIME")

S3_CLIENT = boto3.client(
    "s3",
    endpoint_url=AWS_ENDPOINT_URL,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION 
)

HISTORY = {}

############################################################

def Find_New_Files(pattern, before_set):
    after_set = set(glob.glob(pattern))
    return list(after_set - before_set)

def Get_Steps_From_Cpt(cpt_file):
    try:
        result = subprocess.run( ["gmx", "dump", "-cp", cpt_file], capture_output=True, text=True, check=True)
        for line in result.stdout.splitlines():
            m = re.search(r'step\s*=\s*(\d+)', line) # None if no match is found
            if m: # if m is not None
                return int(m.group(1))
    except Exception as e:
        print(f"Error processing checkpoint file {cpt_file}: {e}") 
    return None

# Upload source to bucket/prefix/folder/target
# Not output any messages to stdout
def Uploader_Chunked_Parallel(
    task,
    source, 
    bucket, prefix, folder, target,
    chunk_size_mbtype, # e.g., "10M"
    concurrency        #  e.g., "10"
):
    s3 = S3_CLIENT 

    # Get the size of source file in MB before uploade
    try:
        fileSize = os.path.getsize(source)
        fileSizeMB = fileSize / 1_000_000
    except Exception as e:
        return {f"{task}_error_filesize": str(e)}
    
    chunk_size_mb = int(''.join(filter(str.isdigit, chunk_size_mbtype)))
    multipart_chunksize = chunk_size_mb * 1_000_000
    max_concurrency = int(concurrency)
    if prefix == "":
        key = f"{folder}/{target}"
    else:
        key = f"{prefix}/{folder}/{target}"

    config = TransferConfig(
        multipart_chunksize=multipart_chunksize,
        max_concurrency=max_concurrency, # ignored if use_threads is False
        use_threads=True
    )

    # Start
    startTime = time.time()
    
    try:
        s3.upload_file(
            Filename=source,
            Bucket=bucket,
            Key=key,
            Config=config
        )
    except Exception as e:
        return { f"{task}_error_upload": str(e) }
    
    # End
    timeSec = time.time() - startTime
    throughputMbps = (fileSizeMB * 8) / timeSec 

    return {
        "upload": target,
        f"{task}_size_MB": f"{fileSizeMB:.3f}",
        f"{task}_time_second": f"{timeSec:.3f}",
        f"{task}_throughput_Mbps": f"{throughputMbps:.3f}"
    }

# Download from bucket/folder/ID/source to target
# Not output any messages to stdout
def Downloader_Chunked_Parallel(
    task,
    bucket, prefix, folder, source,
    target,
    chunk_size_mbtype,  # e.g., "10M"
    concurrency         # e.g., "10"
):
    
    s3 = S3_CLIENT 
    
    chunk_size_mb = int(''.join(filter(str.isdigit, chunk_size_mbtype)))
    multipart_chunksize = chunk_size_mb * 1_000_000
    max_concurrency = int(concurrency)
    if prefix == "":
        key = f"{folder}/{source}"
    else:
        key = f"{prefix}/{folder}/{source}"

    config = TransferConfig(
        multipart_chunksize=multipart_chunksize,
        max_concurrency=max_concurrency,  # ignored if use_threads is False
        use_threads=True
    )

    # Start
    startTime = time.time()

    try:
        s3.download_file(
            Bucket=bucket,
            Key=key,
            Filename=target,
            Config=config
        )
    except Exception as e:
        return { f"{task}_error_download": str(e) }

    # Check the size of the downloaded file after download
    try:
        fileSize = os.path.getsize(target)
        fileSizeMB = fileSize / 1_000_000
    except Exception as e:
        return { f"{task}_error_filesize": str(e) }

    # End
    timeSec = time.time() - startTime
    throughputMbps = (fileSizeMB * 8) / timeSec 

    return {
        "download": source,
        f"{task}_size_MB": f"{fileSizeMB:.3f}",
        f"{task}_time_second": f"{timeSec:.3f}",
        f"{task}_throughput_Mbps": f"{throughputMbps:.3f}"
    }

############################################################

# Trigger node reallocation if a node is not suitable
# https://docs.salad.com/products/sce/container-groups/imds/imds-reallocate
def Reallocate(reason):
    local_run = True if 'local' in SALAD_MACHINE_ID.lower() else False
    
    print(reason)

    if (local_run):  # Run locally
        print("Call the exitl to restart ......", flush=True) 
        os.execl(sys.executable, sys.executable, *sys.argv)
    else:            # Run on SaladCloud
        print("Call the IMDS reallocate ......", flush=True)
        url = "http://169.254.169.254/v1/reallocate"
        headers = {'Content-Type': 'application/json',
                   'Metadata': 'true'}
        body = {"Reason": reason}
        _ = requests.post(url, headers=headers, json=body)
        time.sleep(10)

############################################################

def Get_GPU():
    try:
        result = {}

        cmd = 'nvidia-smi'
        output = subprocess.check_output(cmd, shell=True, text=True)
        output = output.split("\n")[2]
        output = output.split("CUDA Version: ")[-1]
        result['cuda'] = float(output.split(" ")[0])

        cmd = 'nvidia-smi --query-gpu=gpu_name,memory.total,memory.used,memory.free,utilization.memory,temperature.gpu,utilization.gpu --format=csv,noheader'
        output = subprocess.check_output(cmd, shell=True, text=True)
        result['gpu'], result['vram_total'], result['vram_used'], result['vram_free'], result['vram_utilization'], result['gpu_temperature'], result['gpu_utilization'] = output.strip().split(', ')
    
    except Exception as e:
        return None
    
    return result 

def History_Initialize(filename, task_name):
    global HISTORY
    tTime = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S")  

    if task_name == "START":
        HISTORY['task_history'].append( ( tTime, SALAD_MACHINE_ID, 'start') )
    else:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                HISTORY = json.load(f)     
        else:
            HISTORY = { 'task_name': task_name,
                        'task_done': False,
                        'task_creation_time': TASK_CREATION_TIME,
                        'task_completion_time': "",
                        'task_duration': "",
                        'task_history': []}
        HISTORY['task_history'].append( ( tTime, SALAD_MACHINE_ID, 'online', Get_GPU() ) )

    with open(filename, 'w') as f:
        json.dump(HISTORY, f, indent=2)
    
def History_Record(filename, steps, steps_done, max_steps, task_completed):
    global HISTORY
    tTime = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S")

    HISTORY['task_history'].append( ( tTime, SALAD_MACHINE_ID, 'run_chunk', 
                                     { 'chunk_steps': steps, 'completed_steps': steps_done, 'total_steps:':max_steps} ) )

    if task_completed:
        HISTORY['task_history'].append( ( tTime, SALAD_MACHINE_ID, 'end' ) )
        HISTORY['task_done'] = True
        HISTORY['task_completion_time'] = tTime
        start =  datetime.strptime(HISTORY['task_creation_time'],"%Y-%m-%d %H:%M:%S")
        end = datetime.strptime(HISTORY['task_completion_time'],"%Y-%m-%d %H:%M:%S")
        HISTORY['task_duration'] = str(end - start)
    
    with open(filename, 'w') as f:
        json.dump(HISTORY, f, indent=2)
