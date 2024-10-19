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

