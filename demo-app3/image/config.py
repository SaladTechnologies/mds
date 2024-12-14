import os
import json
import time
import random 
from enum import Enum
import speedtest
from pythonping import ping
import subprocess
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()


kelpie_job_id     = os.getenv("KELPIE_JOB_ID", "TEST")
kelpie_state_file = os.getenv("KELPIE_STATE_FILE", "TEST")
salad_machine_id  = os.getenv("SALAD_MACHINE_ID", "LOCAL") # Assigned automatically while running on SaladCloud
ULSPEED           =  int(os.getenv("ULSPEED", "0")) # Mbps
DLSPEED           =  int(os.getenv("DLSPEED", "0")) # Mbps


INITIAL_CHECKS = "intial_checks.txt"


# Trigger the node reallocation
# Trigger reallocation here if a node is not suitable: http://169.254.169.254/v1/reallocate
# https://docs.salad.com/products/sce/container-groups/imds/imds-reallocate
def Reallocate(reason):

    local_run = True if salad_machine_id == "LOCAL" else False
    print(reason)
    if (local_run):  # Run locally
        print("Call the exit(1) ......")
        os._exit(1)
    else:        # Run on SaladCloud
        print("Call the IMDS reallocate ......")
        url = "http://169.254.169.254/v1/reallocate"
        headers = {'Content-Type': 'application/json',
                   'Metadata': 'true'}
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
    local_run = True if salad_machine_id == "LOCAL" else False

    environment= {}

    if not local_run:       # Skip the initial checks if run locally    
        # Network test: bandwidth
        country, _, _, dlspeed, ulspeed = network_test() 
        if ulspeed < ULSPEED or dlspeed < DLSPEED: # Node filtering
            Reallocate("poor network bandwith")

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