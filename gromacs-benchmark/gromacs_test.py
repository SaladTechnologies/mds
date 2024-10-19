import subprocess
import requests
import os
import time
from dotenv import load_dotenv


load_dotenv()
os.makedirs('outputs', exist_ok=True)


g_start = time.perf_counter()


Is_Debug = True
cores = os.getenv("CORES", "8")
nsteps = os.getenv("NSTEPS", "200000")
device = os.getenv("DEVICE", "CUDA") # 
models = ['1','2','3','4','5','6']


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
    result['error'] = f"An error occurred while running {cmd} : {e}" 
    print(result)
    if benchmark_url != "":
        requests.post( f"{benchmark_url}/{benchmark_sl_id}",json=result,headers=benchmark_headers)
    os._exit(1) 


print("*" * 60, "The system info:")
print(result)


try:
    for model in models:
        print("*" * 60,"Run the model:",model)
        
        if device == 'CUDA':
            cmd = f"gmx mdrun -s systems/{model}.tpr -nb gpu -pme gpu -bonded gpu -update gpu -ntmpi 1 -ntomp {cores} -pin on -pinstride 1 -nsteps {nsteps} -deffnm outputs/{model}"
        else:
            cmd = f"gmx mdrun -s systems/{model}.tpr -nb cpu -pme cpu -bonded cpu -update cpu -ntmpi 1 -ntomp {cores} -pin on -pinstride 1 -nsteps {nsteps} -deffnm outputs/{model}"
     
        temp_start = time.perf_counter()
        output = subprocess.check_output(cmd, shell=True, text=True)
        temp_end = time.perf_counter()

        file = f"outputs/{model}.log"

        with open(file, 'r') as f:
            output = f.read()           
        
        output = output.split("\n")[-4]
        output = output.split()[1]

        result[model + '_steps']        = nsteps
        result[model + '_elapsed_time'] = "{:.6f}".format( temp_end - temp_start )
        result[model + '_ns_per_day']   = "{:.6f}".format( float(output)) 

except Exception as e:
    g_end = time.perf_counter()
    result['test_time'] = "{:.3f}".format(g_end - g_start)  
    result['error'] = f"An error occurred while running {cmd} : {e}"
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
vram_used : 628 MiB
vram_free : 23699 MiB
vram_utilization : 0 %
gpu_temperature : 40
gpu_utilization : 2 %
vram_available : 0.964
1_steps : 200000
1_elapsed_time : 97.772689
1_ns_per_day : 178.075000
2_steps : 200000
2_elapsed_time : 65.786156
2_ns_per_day : 531.461000
3_steps : 200000
3_elapsed_time : 167.381495
3_ns_per_day : 213.344000
4_steps : 200000
4_elapsed_time : 298.425179
4_ns_per_day : 117.933000
5_steps : 200000
5_elapsed_time : 995.262838
5_ns_per_day : 34.807000
6_steps : 200000
6_elapsed_time : 1791.016135
6_ns_per_day : 19.340000
test_time : 3415.719
************************************************************ The end
'''