from storage import Data_Sync, Data_Async_Upload, Get_Uploader_State, Wait, test_file_name 
from config import INITIAL_CHECKS, salad_machine_id, kelpie_job_id, kelpie_state_file, Reallocate, Initial_Check
import os
import time
import json
from datetime import datetime, timezone


g_first_job = False if os.path.exists( os.path.abspath(INITIAL_CHECKS) ) else True
if g_first_job:
    g_environment = Initial_Check()
    with open(os.path.abspath(INITIAL_CHECKS), 'w') as f:
        f.write(json.dumps(g_environment))
else:
    with open(os.path.abspath(INITIAL_CHECKS), 'r') as file:
        g_environment = json.load(file)

print(g_environment)    

# The job input: begin, end
# To calculate the sum of the series from start to end, which includes start, start + 1, start + 2, and so on.

# The job state:
# (1) running data, t and sum_t, meaning the sum from start to t.
# (2) logs,  all machines that have participated in executing this job.

# The job output: sum

# The 3 folders should be existed in the container: /app/data/input/, /app/data/state/, /app/data/output/
input_file  = os.path.join( os.path.dirname(__file__), 'data/input/input.txt'   ) # input
state_file  = os.path.join( os.path.dirname(__file__), 'data/state/state.txt'   ) # state - running data
logs_file   = os.path.join( os.path.dirname(__file__), 'data/state/logs.txt'    ) # state - logs
output_file = os.path.join( os.path.dirname(__file__), 'data/output/output.txt' ) # output

test_file   = os.path.join( os.path.dirname(__file__), test_file_name  ) # test file


files = [input_file, state_file, logs_file, output_file]
for file in files:
    if os.path.exists( file ):
        os.remove( file )


# Use environment variables to pass information
state_saving_internal = float( os.getenv('STATE_SAVING_INTERVAL', "10.0") )  # second
step_running_time     = float( os.getenv('STEP_RUNNING_TIME',      "1.0") )  # second

bucket        = os.getenv("bucket","")
before_folder = os.getenv("before","")
during_folder = os.getenv("during","")
after_folder  = os.getenv("after","")

cloud_input_file  = before_folder + "/input.txt"  
cloud_test_file   = during_folder + "/" + test_file_name 
cloud_state_file  = during_folder + "/state.txt"     
cloud_logs_file   = during_folder + "/logs.txt"
cloud_output_file = after_folder  + "/output.txt"

#print(cloud_input_file, cloud_test_file, cloud_state_file,cloud_logs_file, cloud_output_file)


######################################## Read the logs
g_logs = []
try:
    Data_Sync(cloud_logs_file, bucket, logs_file, upload_local_to_cloud=False)
    with open(logs_file, 'r') as f:
        for temp in f.read().splitlines():
            g_logs.append(temp)
except Exception as e:
    #print("Error:", str(e), flush = True)
    print("No logs file or download error !", flush=True) # Tolerable

######################################## Start logging this time
now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
g_logs.append(f'UTC Time: {now} - Machine ID: {salad_machine_id} - Begin processing the job {kelpie_job_id} - {json.dumps(g_environment)}') # add this node info

######################################## Read the job input: start, end
try:
    Data_Sync(cloud_input_file, bucket, input_file, upload_local_to_cloud=False)
    with open(input_file, 'r') as f:
        g_Start, g_End = f.read().splitlines()
        g_Start, g_End = int(g_Start), int(g_End)
except Exception as e:
    print("Error:", str(e), flush = True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    log = f'UTC Time: {now} - {salad_machine_id} - No input file'
    print(log, flush=True) 
    g_logs.append(log)
    with open(logs_file, 'w') as f:  # Save the logs using 'during'
        for item in g_logs[0:-1]:
            f.write(f"{item}\n")
        f.write(g_logs[-1])
    Data_Sync(logs_file, bucket, cloud_logs_file, upload_local_to_cloud=True)
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
    Data_Sync(logs_file, bucket, cloud_logs_file, upload_local_to_cloud=True)
    exit(0) # The job has finished although it failed

print(f'The job is to calculate the sum of {g_Start} ... {g_End}', flush=True)

######################################## Read the running data: t and sum_t
g_finishedStep = g_Start - 1
g_tempSum = 0
try:
    Data_Sync(cloud_state_file, bucket, state_file, upload_local_to_cloud=False)
    with open(state_file, 'r') as f:
        g_finishedStep, g_tempSum = f.read().splitlines()
        g_finishedStep, g_tempSum = int(g_finishedStep), int(g_tempSum)
        print(f'Unfinished job, resume from the previous state: the sum of {g_Start} ... {g_finishedStep} is {g_tempSum}', flush=True)
except Exception as e:
    #print("Error:", str(e), flush = True)
    print('No state file or download error, start from scratch !', flush=True) # Tolerable

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
        percentage = "{:0.2%}".format((x - g_Start + 1) / (g_End - g_Start + 1))
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

        temp  = Get_Uploader_State()
        print(temp)
        if temp["pending"] > 6 or temp["error"] > 3:
            Reallocate("Upload error or backlog!")

        Data_Async_Upload(logs_file,  bucket, cloud_logs_file,  last = False ,logger =  None)    
        Data_Async_Upload(state_file, bucket, cloud_state_file, last = False, logger =  None)    
        Data_Async_Upload(test_file,  bucket, cloud_test_file,  last = False, logger = g_logs)            


# The simulation job is finished at this point 
# There might be some addtional steps after the last save state

Wait() # Wait until all previous uploads are finished

# Final output
with open(output_file, 'w') as f:
    f.write(f"{g_tempSum}")

# Final logs
now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
g_logs.append(f'UTC Time: {now} - Machine ID: {salad_machine_id} - The job {kelpie_job_id} is done') # add this node info
with open(logs_file, 'w') as f:  # Save the logs using 'during'
    for item in g_logs[0:-1]:
        f.write(f"{item}\n")
    f.write(g_logs[-1])

Data_Async_Upload(output_file, bucket, cloud_output_file, last = False,  logger = None)   
Data_Async_Upload(logs_file,   bucket, cloud_logs_file,   last = True,   logger = None) # The upload thread exits     

Wait() # Wait until all previous uploads are finished

print(f'The job output: the sum of {g_Start} ... {g_End} is {g_tempSum}', flush=True)
#print(g_logs)

exit(0)

 