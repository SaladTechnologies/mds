import os
import json
import time
from datetime import datetime, timezone
import random 
from enum import Enum
import speedtest
from pythonping import ping
import subprocess
import requests
import csv
from dotenv import load_dotenv
load_dotenv()


# Access to the Cloudflare R2 
cloudflare_url    = os.getenv("CLOUDFLARE_ENDPOINT_URL", "")
cloudflare_region = os.getenv("CLOUDFLARE_REGION", "")
cloudflare_id     = os.getenv("CLOUDFLARE_ID", "")
cloudflare_key    = os.getenv("CLOUDFLARE_KEY", "")


SALAD_MACHINE_ID = os.getenv("SALAD_MACHINE_ID", "LOCAL") # Assigned automatically while running on SaladCloud
BUCKET           =  os.getenv("BUCKET", "transcripts")
FOLDER           =  os.getenv("FOLDER", "high_performance_storage")
SIZE             =  os.getenv("SIZE", "200")        # MiB 
ULSPEED          =  int(os.getenv("ULSPEED", "10")) # Mbps
DLSPEED          =  int(os.getenv("DLSPEED", "20")) # Mbps

# Create the configuration file for rclone
# https://developers.cloudflare.com/r2/examples/rclone/
filename = os.path.expanduser("~")+"/.config/rclone/rclone.conf"
with open(filename,'w') as f:
    f.write("[r2]\n")
    f.write("type = s3\n")
    f.write("provider = Cloudflare\n")
    f.write("access_key_id = {}\n".format(cloudflare_id))
    f.write("secret_access_key = {}\n".format(cloudflare_key))
    f.write("region = {}\n".format(cloudflare_region))
    f.write("endpoint = {}\n".format(cloudflare_url))
    f.write("no_check_bucket = true")


# Create the test file
def Create_File(size): # MiB
    cmd = f'dd if=/dev/zero of={size}MiB.file bs=1M count={size}'
    print("executing: " + cmd, flush = True)                                                      
    subprocess.run(cmd, shell=True, check=True, stderr=subprocess.PIPE)
    return f'{size}MiB.file'


# upload_local_to_cloud=True,  uploading
# upload_local_to_cloud=False, downloading
def Data_Sync(source, bucket, target, upload_local_to_cloud=True, chunk_size_mbype="10M", concurrency="10"):
    t_start  = time.perf_counter()
    if upload_local_to_cloud:
        cmd = f'rclone copyto {source} r2:{bucket}/{target} --s3-chunk-size={chunk_size_mbype} --transfers={concurrency} --ignore-times'
    else:
        cmd = f'rclone copyto r2:{bucket}/{source} {target} --s3-chunk-size={chunk_size_mbype} --transfers={concurrency} --ignore-times'
    print("executing: " + cmd, flush = True)                                                      
    subprocess.run(cmd, shell=True, check=True, stderr=subprocess.PIPE)
    t_end = time.perf_counter()
    t_duration = round((t_end - t_start), 3) # seco

    if upload_local_to_cloud:
        file_size = round(os.path.getsize(source)/1_000_000, 3)  # MB, not MiB 
    else:
        file_size = round(os.path.getsize(target)/1_000_000, 3)  # MB, not MiB
    
    throughput = round(file_size * 8/t_duration, 3)
    if upload_local_to_cloud:
        print(f"The file size (MB):{file_size}, the uploading time (second): {t_duration}, the uploading throught (Mbps): {throughput}", flush = True)
    else:
        print(f"The file size (MB):{file_size}, the downloading time (second): {t_duration}, the downloading throught (Mbps): {throughput}", flush = True)
    
    return file_size, t_duration, throughput


# Remove a single file locally or in Cloudflare R2
def Data_Remove(bucket, target):
    if bucket == "":
        cmd = f'rm {target}'
    else:
        cmd = f'rclone deletefile r2:{bucket}/{target}'
    print("executing: " + cmd, flush = True)                                                      
    subprocess.run(cmd, shell=True, check=True, stderr=subprocess.PIPE)
    

# Download and save the test results from Cloudflare R2 into a local file
def Data_Get(bucket, folder, filename):
    test_results = []
    cmd = f'rclone lsf r2:{bucket}/{folder}'
    print("executing: " + cmd, flush = True)                                                      
    output = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = output.stdout.decode('utf-8')
    lines = result.splitlines()

    for line in lines:
        cmd = f'rclone cat r2:{bucket}/{folder}/{line}'
        print("executing: " + cmd, flush = True)   
        temp = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        content = temp.stdout.decode('utf-8')
        content = json.loads(content) 
        content["MACHINE_ID"] = line.split(".")[0]
        test_results.append(content)
    
    with open(filename, mode="w", newline="") as file:
        fieldnames = test_results[0].keys()
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(test_results)

    return test_results


# Trigger the node reallocation
# Trigger reallocation here if a node is not suitable: http://169.254.169.254/v1/reallocate
# https://docs.salad.com/products/sce/container-groups/imds/imds-reallocate
def Reallocate(local, reason):
    print(reason)
    if (local):  # Run locally
        print("Call the exit(1) ......")
        os._exit(1)
    else:        # Run on SaladCloud
        print("Call the IMDS reallocate ......")
        url = "http://169.254.169.254/v1/reallocate"
        headers = {'Content-Type': 'application/json', 'Metadata': 'true'}
        body = {"Reason": reason}
        response = requests.post(url, headers=headers, json=body)
        print(response) # The instance will become inactive after a few seconds
        print("See you later")
        time.sleep(10)


# Test network bandwdith
def network_test():
    print("Test the network speed ....................", flush=True)
    try:
        speed_test = speedtest.Speedtest()
        bserver = speed_test.get_best_server()
        dlspeed = int(speed_test.download() / (1000 * 1000))  # Convert to Mbps, not Mib
        ulspeed = int(speed_test.upload() / (1000 * 1000))  # Convert to Mbps, not Mib
        latency = bserver['latency'] # the latency to the test server
        country = bserver['country'] 
        location = bserver['name']
    except Exception as e:  
        return "", "", 99999, 0, 0
    return country, location, latency, dlspeed, ulspeed    


# Test network latency
# Only the root user can run this code - no issue in containers
def ping_test(tCount=10):
    print("Test the latency ....................", flush=True)
    try:
        print("To: ec2.us-east-1.amazonaws.com")
        temp = ping('ec2.us-east-1.amazonaws.com', interval=1, count=tCount, verbose=True)
        latency_useast1 = temp.rtt_avg_ms      
        print("To: ec2.eu-central-1.amazonaws.com")  
        temp = ping('ec2.eu-central-1.amazonaws.com', interval=1, count=tCount,verbose=True)
        latency_eucentral1 = temp.rtt_avg_ms
    except Exception as e:  
        return 99999,99999
    return latency_useast1, latency_eucentral1


# Read the CUDA Version
def Get_CUDA_Version():
    try:
        cmd = 'nvidia-smi'
        output = subprocess.check_output(cmd, shell=True, text=True)
        output = output.split("\n")[2]
        output = output.split("CUDA Version: ")[-1]
        version = float(output.split(" ")[0])
    except Exception as e: 
        return 0
    return version 


# Get the GPU info
def Get_GPU():
    try:
        result = {}
        cmd = 'nvidia-smi --query-gpu=gpu_name,memory.total,memory.used,memory.free,utilization.memory,temperature.gpu,utilization.gpu --format=csv,noheader'
        output = subprocess.check_output(cmd, shell=True, text=True)
        result['gpu'], result['vram_total'], result['vram_used'], result['vram_free'], result['vram_utilization'], result['gpu_temperature'], result['gpu_utilization'] = output.strip().split(', ')
    except Exception as e:
        return {}
    return result 


def Initial_Check():
        
    # True:  local run; False: run on SaladCloud
    local_run = True if SALAD_MACHINE_ID == "LOCAL" else False

    environment= {}

    if not local_run:       # Skip the initial checks if run locally    
        # Network test: bandwidth
        country, _, _, dlspeed, ulspeed = network_test() 
        if ulspeed < ULSPEED or dlspeed < DLSPEED: # Node filtering
            Reallocate(local_run, "poor network bandwith")

        # Network test: latency to some locations
        latency_us, latency_eu = ping_test(tCount = 10) 

        # Initial check: CUDA Version, VRAM and others
        CUDA_version = Get_CUDA_Version()
        GPU = Get_GPU()

        environment = { "Country":       country,
                          "DL Mbps":       dlspeed, 
                          "UL Mbps":       ulspeed,
                          "RTT to US-East ms": latency_us,
                          "RTT to EU-Cent ms": latency_eu,
                          "GPU":           GPU['gpu'],
                          "CUDA":          CUDA_version,
                          "VRAM MiB":      GPU['vram_total'],
                          "VRAM_Free":     GPU['vram_free'] }

    
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") # Go-live time
    environment["UTC Time-Start"] = now 

    return environment