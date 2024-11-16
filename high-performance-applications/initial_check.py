from imds_reallocate import Reallocate
from check_gpu import Get_CUDA_Version,Get_GPU
from check_network import network_test,ping_test

import os
import uuid
import json
from datetime import datetime, timezone

# If run the container locally, use a random ID
LOCAL_MACHINE = str(uuid.uuid4()) 
# Get the ID if running on SaladCloud
salad_machine_id = os.getenv("SALAD_MACHINE_ID", LOCAL_MACHINE)

# True if running locally  
g_local_run = True if salad_machine_id == LOCAL_MACHINE else False

# The instance only run a few seconds to perform the initial check, the associated cost is negligible.
# Filer the node based on your need: bandwidth, latency to some locations, CUDA version and VRAM.
# If the node is not ideal, call the Reallocate for a more suitable node

if g_local_run:
    g_environment= {}
else:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") # Go-live time

    # Network test: bandwidth
    _, _, _, g_dlspeed, g_ulspeed = network_test() # Mbps - M bit per second
    if g_ulspeed < 5 or g_dlspeed < 20: # 20+ Mbps DL and 5+ Mbps UL are required to run this app
        Reallocate(g_local_run, "poor network bandwith") # You can put any reason here, which be used for Salad to improve the service 

    # Network test: latency to some locations
    g_latency_us, g_latency_eu = ping_test(tCount = 10) 

    # Initial check: CUDA Version, VRAM and others
    g_CUDA_version = Get_CUDA_Version()
    g_GPU = Get_GPU()

    g_environment = { "DL Mbps":       g_dlspeed, 
                      "UL Mbps":       g_ulspeed,
                      "Latency to US-East ms": g_latency_us,
                      "Latency to EU-Cent ms": g_latency_eu,
                      "GPU":           g_GPU['gpu'],
                      "CUDA":          g_CUDA_version,
                      "VRAM MiB":      g_GPU['vram_total'],
                      "VRAM_Free":     g_GPU['vram_free'],
                      "UTC Time Go-live": now }

    #print( g_dlspeed, g_ulspeed, g_latency_us, g_latency_eu )
    #print(g_CUDA_version)
    #print(g_GPU)
    print(g_environment)

# Warm up the model by running a few inference tasks 
# Compare the actual performance with the predefined threshold