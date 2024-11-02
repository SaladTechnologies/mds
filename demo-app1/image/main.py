from config import INITIAL_CHECKS
from config import Reallocate, network_test, ping_test, Get_CUDA_Version, Get_GPU
import os
import time
import uuid
import json
from datetime import datetime, timezone


salad_machine_id = os.getenv("SALAD_MACHINE_ID", "LOCAL")

# True:  local run
# False: run on SaladCloud
g_local_run = True if salad_machine_id == "LOCAL" else False

# The code is first run by the Kelpie worker in this node
g_first_job = False if os.path.exists( os.path.abspath(INITIAL_CHECKS) ) else True

if g_local_run:       # Skip the initial checks if run locally
    g_environment= {}
elif not g_first_job: # Already finished the initial checks
    with open(os.path.abspath(INITIAL_CHECKS), 'r') as file:
        g_environment = json.load(file)
else:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") # Go-live time

    # Network test: bandwidth
    _, _, _, g_dlspeed, g_ulspeed = network_test() 
    if g_ulspeed < 5 or g_dlspeed < 20: # 20+ Mbps DL and 5+ Mbps UL are required to run this app
        Reallocate(g_local_run, "poor network bandwith")

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

    with open(os.path.abspath(INITIAL_CHECKS), 'w') as f:
        f.write(json.dumps(g_environment))

print(g_environment)    

# The job input: begin, end
# To calculate the sum of the series from start to end, which includes start, start + 1, start + 2, and so on.

# The job state:
# (1) running data, t and sum_t, meaning the sum from start to t.
# (2) logs,  all machines that have participated in executing this job.

# The job output: sum

# The 3 folders should be existed in the container: /app/data/input/, /app/data/state/, /app/data/output/

# When the Kelpie worker runs the code after retrieving a job: it will first clear the 3 folders;
# and then download the input and the state from the Cloud Storage and save them here (input, state).

input_file  = os.path.join( os.path.dirname(__file__), 'data/input/input.txt'   ) # input
state_file  = os.path.join( os.path.dirname(__file__), 'data/state/state.txt'   ) # state - running data
logs_file   = os.path.join( os.path.dirname(__file__), 'data/state/logs.txt'    ) # state - logs
output_file = os.path.join( os.path.dirname(__file__), 'data/output/output.txt' ) # output

# Use environment variables to pass information
state_saving_internal = float( os.getenv('STATE_SAVING_INTERVAL', "10.0") )  # second
step_running_time     = float( os.getenv('STEP_RUNNING_TIME',      "1.0") )  # second


######################################## Read the logs
g_logs = []
try:
    with open(logs_file, 'r') as f:
        for temp in f.read().splitlines():
            g_logs.append(temp)
except FileNotFoundError:
    print("No logs file", flush=True) # Tolerable

######################################## Start logging this time
now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
g_logs.append(f'UTC Time: {now} - Machine ID: {salad_machine_id} - Begin processing the job - {json.dumps(g_environment)}') # add this node info

######################################## Read the job input: start, end
try:
    with open(input_file, 'r') as f:
        g_Start, g_End = f.read().splitlines()
        g_Start, g_End = int(g_Start), int(g_End)
except FileNotFoundError:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    log = f'UTC Time: {now} - {salad_machine_id} - No input file'
    print(log, flush=True) 
    g_logs.append(log)
    with open(logs_file, 'w') as f:  # Save the logs using 'during'
        for item in g_logs[0:-1]:
            f.write(f"{item}\n")
        f.write(g_logs[-1])
    exit(0) # The job has finished although it failed

######################################## Handle the exception
if g_Start > g_End:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    log = f'UTC Time: {now} - {salad_machine_id} - Wrong input'
    print(log, flush=True) 
    g_logs.append(log)
    with open(logs_file, 'w') as f:  # Save the logs using 'during'
        for item in g_logs[0:-1]:
            f.write(f"{item}\n")
        f.write(g_logs[-1])
    exit(0) # The job has finished although it failed

print(f'The job is to calculate the sum of {g_Start} ... {g_End}', flush=True)

######################################## Read the running data: t and sum_t
g_finishedStep = g_Start - 1
g_tempSum = 0
try:
    with open(state_file, 'r') as f:
        g_finishedStep, g_tempSum = f.read().splitlines()
        g_finishedStep, g_tempSum = int(g_finishedStep), int(g_tempSum)
        print(f'Unfinished job, resume from the previous state: the sum of {g_Start} ... {g_finishedStep} is {g_tempSum}', flush=True)
except FileNotFoundError:
    print('New job, start from scratch', flush=True)

######################################## Run the job - long running and interruptible
time_start = time.perf_counter()
for x in range(g_finishedStep+1, g_End+1):

    ########## # GPU Compute: start for a specific steps
    g_tempSum = g_tempSum + x

    t_start  = time.perf_counter()
    while True:
        t_end = time.perf_counter()
        if (t_end - t_start) > step_running_time:
            break
    ########## # GPU Compute: end

    time_end = time.perf_counter()

    if (time_end - time_start) > state_saving_internal:
        time_start = time.perf_counter()

        ######################################## Record this event
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        percentage = "{:0.2%}".format((x - g_Start) / (g_End - g_Start))
        g_logs.append(f'UTC Time: {now} - Saving the state at the step {x}, finished {percentage}') # Record this event
        ######################################## 

        with open(logs_file, 'w') as f:  # Save the logs
            for item in g_logs[0:-1]:
                f.write(f"{item}\n")
            f.write(g_logs[-1])

        with open(state_file, 'w') as f:  # Save the running data: t and sum_t
                                          # The Kelpie worker will upload this folder if any changes occur while the code is running
            temp = str(x) + '\n' + str(g_tempSum)
            f.write(temp)
            print(f'Save the status every {state_saving_internal} seconds: the sum of {g_Start} ... {x} is {g_tempSum}', flush=True)


# The simulation job is finished at this point 
# There might be some addtional steps after the last save state
now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
g_logs.append(f'UTC Time: {now} - Machine ID: {salad_machine_id} - The job is done') # add this node info
with open(logs_file, 'w') as f:  # Save the logs using 'during'
    for item in g_logs[0:-1]:
        f.write(f"{item}\n")
    f.write(g_logs[-1])


# Save the job output using 'after'
with open(output_file, 'w') as f:
    f.write(f"{g_tempSum}")


print(f'The job output: the sum of {g_Start} ... {g_End} is {g_tempSum}', flush=True)
exit(0)

# If code exits normally, the Kelpie worker will upload this folder and report the job status as completed.
 