import subprocess
import requests
import os
import time
from dotenv import load_dotenv
load_dotenv()


g_start = time.perf_counter()


Is_Debug = True
duration = os.getenv("DURATION", 60)
device = os.getenv("DEVICE", "CUDA") # CPU, 16 x vCPU
models = ['pme','apoa1pme','amber20-cellulose','amber20-stmv','amoebapme']

result = {}
result['test_device'] = device
result['salad-machine-id']         = os.getenv("SALAD_MACHINE_ID", "LOCAL")  # Passed by SaladCloud
result['salad-container-group-id'] = os.getenv("SALAD_CONTAINER_GROUP_ID", "LOCAL_TEST") # Passed by SaladCloud


# Access to the Job Reporting System
benchmark_url = os.getenv("REPORTING_API_URL", "")
benchmark_id = os.getenv("BENCHMARK_ID", "")   # Test Records
benchmark_sl_id = benchmark_id + "-sl"         # System Logs 
benchmark_auth_header = os.getenv("REPORTING_AUTH_HEADER", "")
benchmark_auth_value = os.getenv("REPORTING_API_KEY", "")
benchmark_headers = { benchmark_auth_header: benchmark_auth_value }


def getValue(inputs,key):
    for one in inputs:
        if key in one:
            return one.replace(key+": ","") 
    return None
        

try:
    cmd = 'nvidia-smi'
    output = subprocess.check_output(cmd, shell=True, text=True)
    output = output.split("\n")[2]
    output = output.split("CUDA Version: ")[-1]
    result['cuda_version'] = output.split(" ")[0]

    cmd = 'nvidia-smi --query-gpu=driver_version,gpu_name,memory.total,memory.used,memory.free,utilization.memory,temperature.gpu,utilization.gpu --format=csv,noheader'
    output = subprocess.check_output(cmd, shell=True, text=True)
    result['nvidia_driver'], result['gpu'], result['vram_total'], result['vram_used'], result['vram_free'], result['vram_utilization'], result['gpu_temperature'], result['gpu_utilization'] = output.strip().split(', ')
    result['vram_available'] = "{:.3f}".format( float(result['vram_free'].split(" ")[0]) / float(result['vram_total'].split(" ")[0]) )
except Exception as e:
    g_end = time.perf_counter()
    result['test_time'] = "{:.3f}".format(g_end - g_start)  
    result['error'] = f"An error occurred while running nvidia-smi: {e}" 
    print(result)
    if benchmark_url != "":
        requests.post( f"{benchmark_url}/{benchmark_sl_id}",json=result,headers=benchmark_headers)
    os._exit(1) 


print("*" * 60, "The system info:")
print(result)


try:
    for model in models:
        print("*" * 60,"Run the model:",model)
        cmd = f"python benchmark.py --platform={device} --test={model} --seconds={duration}"
        output = subprocess.check_output(cmd, shell=True, text=True)

        print(output)

        output = output.split("\n")
        if model == "pme":
            result ['cpuinfo'] = getValue(output,'cpuinfo')
        result[model + '_steps']        = getValue(output,'steps')
        result[model + '_elapsed_time'] = "{:.6f}".format( float(getValue(output,'elapsed_time')))
        result[model + '_ns_per_day']   = "{:.6f}".format( float(getValue(output,'ns_per_day'))) 
except Exception as e:
    g_end = time.perf_counter()
    result['test_time'] = "{:.3f}".format(g_end - g_start)  
    result['error'] = f"An error occurred while running the benchmarking: {e}"
    print(result)
    if benchmark_url != "":
        requests.post( f"{benchmark_url}/{benchmark_sl_id}",json=result,headers=benchmark_headers)
    os._exit(1) 


g_end = time.perf_counter()
result['test_time'] = "{:.3f}".format(g_end - g_start)  


print("*" * 60,"The final result:")
for x in result.keys():
    print(x, ":",result[x])


if benchmark_url != "":
    requests.post( f"{benchmark_url}/{benchmark_id}",json=result,headers=benchmark_headers)


print("*" * 60,"The end")

'''
************************************************************ The final result:
test_device : CUDA
salad-machine-id : LOCAL
salad-container-group-id : LOCAL_TEST
cuda_version : 12.6
nvidia_driver : 560.94
gpu : NVIDIA GeForce RTX 3090
vram_total : 24576 MiB
vram_used : 646 MiB
vram_free : 23681 MiB
vram_utilization : 0 %
gpu_temperature : 44
gpu_utilization : 2 %
vram_available : 0.964
cpuinfo : AMD Ryzen 9 5900X 12-Core Processor
pme_steps : 173596
pme_elapsed_time : 57.810942
pme_ns_per_day : 1037.775472
apoa1pme_steps : 67990
apoa1pme_elapsed_time : 59.688274
apoa1pme_ns_per_day : 393.667674
amber20-cellulose_steps : 11618
amber20-cellulose_elapsed_time : 57.879736
amber20-cellulose_ns_per_day : 69.371097
amber20-stmv_steps : 4127
amber20-stmv_elapsed_time : 61.088265
amber20-stmv_ns_per_day : 23.348039
amoebapme_steps : 8555
amoebapme_elapsed_time : 59.526707
amoebapme_ns_per_day : 24.834298
test_time : 392.969
************************************************************ The end
'''