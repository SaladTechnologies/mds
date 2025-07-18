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
from salad_cloud_sdk import SaladCloudSdk
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
 
load_dotenv()

# Assigned automatically while running on SaladCloud
SALAD_MACHINE_ID =  os.getenv("SALAD_MACHINE_ID", "LOCAL")

# Access to the Cloudflare R2 bucket 
CLOUDFLARE_ID             = os.getenv("CLOUDFLARE_ID", "")
CLOUDFLARE_KEY            = os.getenv("CLOUDFLARE_KEY", "")
CLOUDFLARE_ENDPOINT_URL   = os.getenv("CLOUDFLARE_ENDPOINT_URL", "")

# Call the SaladCloud API to shutdown the instance when the simulation is completed or failed.
# SaladCloud will introduce a new mechanism that allows the SRCG to shut itself down internally, eliminating the need for the SaladCloud Python SDK and API access.
SALAD_API_KEY        = os.getenv("SALAD_API_KEY","")
ORGANIZATION_NAME    = os.getenv("ORGANIZATION_NAME","")
PROJECT_NAME         = os.getenv("PROJECT_NAME","")
CONTAINER_GROUP_NAME = os.getenv("CONTAINER_GROUP_NAME","") 

MAX_NO_RESPONSE_TIME = int(os.getenv("MAX_NO_RESPONSE_TIME","3600"))
TASK_CREATION_TIME   = os.getenv("TASK_CREATION_TIME", datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S"))

# if not provided, wait forever to keep the SRCG running on SaladCloud
if CLOUDFLARE_ID == "" or CLOUDFLARE_KEY == "" or CLOUDFLARE_ENDPOINT_URL == "":
    while True:
        print("No access to cloud storage, sleep infinity ......", flush=True)
        time.sleep(10)

S3_CLIENT = boto3.client(
    "s3",
    endpoint_url=CLOUDFLARE_ENDPOINT_URL,
    aws_access_key_id=CLOUDFLARE_ID,
    aws_secret_access_key=CLOUDFLARE_KEY,
    region_name="auto",
)

HISTORY = {}
Uploading_Metric = {'failure':0, 'success':0, 'waiting':0,
                    'total_size_MB':0, 'total_time_second':0, 'average_throughput_Mbps': 999, 
                    # 'success_info': [],
                    'failure_info': []
                    }

############################################################

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

# Stop the SRCG (Single-Replica Container Group) when the simulation is completed or failed.
def Shutdown_SRCG():
    
    local_run = True if 'local' in SALAD_MACHINE_ID.lower() else False

    if (local_run):  # Run locally
        print("Call the exit(0) ......", flush=True)
        os._exit(0)
    else:            # Run on SaladCloud
        # if not provided, wait forever to keep the SRCG running
        if not SALAD_API_KEY or not ORGANIZATION_NAME or not PROJECT_NAME or not CONTAINER_GROUP_NAME:
            while True:
                time.sleep(10)
                print("SaladCloud API access unavailable, sleep infinity ......", flush=True)
        
        print("Call the SaladCloud API to shutdown the SRCG ......", flush=True)
        # https://docs.salad.com/reference/saladcloud-api/container-groups/stop-container-group
        sdk = SaladCloudSdk(api_key=SALAD_API_KEY, timeout=10000)
        _ = sdk.container_groups.stop_container_group(
            organization_name = ORGANIZATION_NAME,
            project_name = PROJECT_NAME,
            container_group_name = CONTAINER_GROUP_NAME
        )
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

def History_Initialize(filename, task_name): # task_name, 'start' of 'task name'
    global HISTORY
    tTime = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S")  

    if task_name == "START": # Record the actual start time of simulation
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

############################################################

def Notify_Uploader(upload_task_queue, message):
    upload_task_queue.put(message)

def Upload_Health_Check():
    return(Uploading_Metric) 

def Wait_For_Upload_Completion(upload_task_queue):
    upload_task_queue.put(None) # Notify the uploader thread to terminate
    # Waiting for all checkpoints to upload 
    while True:
        temp = upload_task_queue.qsize() # 1 while None is still in the queue
        if temp > 0:
            print(f"{temp} files are being uploaded ...", flush=True)
            time.sleep(10)
        else:
            break

def Uploader(queue):

    global Uploading_Metric 
    no_response_time = 0
    print("---------> Uploader Thread: starts!", flush=True)

    while True:

        if queue.empty():
            time.sleep(10)
            no_response_time = no_response_time + 10
            if no_response_time > MAX_NO_RESPONSE_TIME:
                print(f"Uploader Thread: no response from the main thread for {MAX_NO_RESPONSE_TIME} seconds", flush=True)
                Reallocate("node performance issue")
            continue

        no_response_time = 0 # Reset
        
        message = queue.get()  # May block here
        
        if message == None:     # Completed - None is the last one in the queue 
            queue.task_done() 
            break # exits
        else:
            result = Uploader_Chunked_Parallel( message['task'],
                                                message['source'],
                                                message['bucket'],
                                                message['prefix'],
                                                message['folder'],
                                                message['target'],
                                                message['chunk_size_mbtype'],
                                                message['concurrency'] )
            
            print(f'---------> Uploader Thread: {result}', flush=True)
            if len(result) > 1:
                Uploading_Metric['success'] += 1
                Uploading_Metric['total_size_MB'] += float(next(v for k, v in result.items() if 'size_MB' in k))
                Uploading_Metric['total_size_MB'] = round(Uploading_Metric['total_size_MB'],3)
                Uploading_Metric['total_time_second'] += float(next(v for k, v in result.items() if 'time_second' in k))
                Uploading_Metric['total_time_second'] = round(Uploading_Metric['total_time_second'],3)
                Uploading_Metric['average_throughput_Mbps'] = round(Uploading_Metric['total_size_MB'] * 8 / Uploading_Metric['total_time_second'],3) 
                # Uploading_Metric['success_info'].append(result)
            else:
                Uploading_Metric['failure'] += 1
                Uploading_Metric['failure_info'].append(result)

            Uploading_Metric['waiting'] = queue.qsize() # Update the number of waiting tasks   

            os.remove(message['source'])

            queue.task_done() # mainly for queue.join(), not for queue.qsize()
    
    print("---------> Uploader Thread: exits!", flush=True)
