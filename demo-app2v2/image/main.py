from config import Retrieve_A_Job, Delete_A_Job  
from config import Uploader, VT_Renewal 
from config import Get_Visibility_Timeout_Health, Get_Upload_Error, Reset_Upload_Error
from config import Wait, Reallocate
from config import s3, WAITING, MAX_UPLOAD_TIME, MAX_UPLOAD_LOG_TIME
from config import network_test, ping_test, Get_CUDA_Version, Get_GPU

import os
import time
import queue
import threading
import shutil
import uuid
import json
from datetime import datetime, timezone


# If run the container locally, use the random ID
LOCAL_MACHINE = str(uuid.uuid4()) 
salad_machine_id = os.getenv("SALAD_MACHINE_ID", LOCAL_MACHINE)
g_continue_node = True # Run on this node 
g_local_run = True if salad_machine_id == LOCAL_MACHINE else False


# The instance only run a few seconds to perform the initial check, 
# so the additional costs for this process are negligible.

# Filer the node based on your need: bandwidth, latency, CUDA version and VRAM.
# If the node is not ideal, then
# call the Reallocate(g_local_run, "This node is not ideal to run this application")


# Network test: latency to some location and bandwidth
_, _, _, g_dlspeed, g_ulspeed = network_test() 

if g_ulspeed < 5 or g_dlspeed < 20: # 20+ Mbps DL and 5+ Mbps UL are required to run this app
    Reallocate(g_local_run, "poor network bandwith")

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
                  "VRAM_Free":     g_GPU['vram_free'] }

#print( g_dlspeed, g_ulspeed, g_latency_us, g_latency_eu )
#print(g_CUDA_version)
#print(g_GPU)
print(g_environment)


input_file  = os.path.join( os.path.dirname(__file__), 'data/input.txt'   ) # input
state_file  = os.path.join( os.path.dirname(__file__), 'data/state.txt'   ) # state
logs_file   = os.path.join( os.path.dirname(__file__), 'data/logs.txt'    ) # logs
output_file = os.path.join( os.path.dirname(__file__), 'data/output.txt'  )  # output


# The main thread --- upload tasks --> the ul thread
upload_task_queue = queue.Queue()
# The main thread <-- Optional(True/False) --- the ul thread, need the ACK for the last upload task when the job is done 
ack_queue = queue.Queue()
# The main thread ---  job handle ---> the vtr thread, to monitor and extend the visibility timeout in AWS SQS
vtr_queue = queue.Queue()

# The ul thread for uploading tasks and removing the temp files
ul_thread = threading.Thread(target=Uploader, args=(upload_task_queue, ack_queue,))
ul_thread.start()
# The vtr thread for extending visibility timeout
vtr_thread = threading.Thread(target=VT_Renewal, args=(vtr_queue, ))
vtr_thread.start()


while True:

    if not g_continue_node: # Need to chanage the node
        Reallocate(g_local_run, "poor network or processing capacity, or no access to Cloudflare")

    jobs = Retrieve_A_Job(WAIT_TIME=5)  # Block here; will exit with non-zero if sth goes wrong, triggering reallocation
    if len(jobs) == 0:
        continue

    job = jobs[0] # Get a job
    print("Retrieved a job: "+ job['message']['folder'], flush=True)
    g_logs = []   # Initialize the jobs
    vtr_queue.put( job ) # Notify the VTR thread to start monitoring and extending the visibility timeout regularly

    BUCKET                = job['message']['bucket']
    FOLDER                = job['message']['folder'] 
    state_saving_internal = float(job['message']['parameters']['STATE_SAVING_INTERVAL'])
    step_running_time     = float(job['message']['parameters']['STEP_RUNNING_TIME'])

    ######################################## Remove the previous job data
    files = [input_file, state_file, logs_file, output_file]
    for file in files:
        if os.path.exists( file ):
            os.remove( file)

    ######################################## Blocking: Load the logs file
    try:
        s3.download_file(BUCKET, FOLDER+"/logs.txt", logs_file )
        with open(logs_file, 'r') as f:
            for temp in f.read().splitlines():
                g_logs.append(temp)        
    except Exception as e:
        print("No logs file or download error !", flush=True) # Tolerable
        
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    g_logs.append(f'Machine ID: {salad_machine_id} - UTC Time: {now} - {json.dumps(g_environment)}') # add this node info

    ######################################## Blocking: Load the state file and resume from the previous state
    g_new_job = True
    try:
        s3.download_file(BUCKET, FOLDER+"/state.txt", state_file )
        with open(state_file, 'r') as f:
            g_start, g_end, g_finishedStep, g_tempSum = f.read().splitlines()
            g_start, g_end, g_finishedStep, g_tempSum = int(g_start), int(g_end), int(g_finishedStep), int(g_tempSum)
        g_new_job = False
        print(f"Unfinished job: begin {g_start}, end {g_end}, t {g_finishedStep}, sum_t {g_tempSum}", flush=True)
    except Exception as e:
        print("No state file or download error !", flush=True) # Tolerable

    ######################################## Blocking: Load the input file if no state, and initialize
    g_continue = True
    if g_new_job:
        try:
            s3.download_file(BUCKET, FOLDER+"/input.txt", input_file )     

            with open(input_file, 'r') as f:
                g_start, g_end = f.read().splitlines()
                g_start, g_end = int(g_start), int(g_end)
            g_finishedStep = g_start - 1   
            g_tempSum = 0       

            if g_start > g_end:
                log = f'{salad_machine_id} - Wrong input'
                print(log, flush=True)
                g_logs.append(log)
                g_continue = False # Intolerable
        except Exception as e:
            log = f'{salad_machine_id} - No input file or download error, ' + str(e)
            print(log, flush=True) 
            g_logs.append(log)
            g_continue = False # Intolerable 
 
        if not g_continue:
            print("The job (or node) has issue !!!!!!")
            with open(logs_file, 'w') as f:   # Create the logs file
                for item in g_logs[0:-1]:
                    f.write(f"{item}\n")
                f.write(g_logs[-1])

            # Copy the data to a temporary file
            logs_temp_file   = os.path.join( os.path.dirname(__file__), 'data/' + str(uuid.uuid4()) ) 
            shutil.copyfile(logs_file, logs_temp_file)

            # Put it into the upload queue 
            task = { "sub_tasks"  : [ { "source": logs_temp_file, "bucket": BUCKET, "target": FOLDER+"/logs.txt" } ],
                     "requiring_ack": True }   
            upload_task_queue.put(task) 

            if Wait(ack_queue, MAX_UPLOAD_LOG_TIME) != WAITING.SUCCESS: # Blocking 
                # This is a big problem: the logs file cannot be uploaded to Cloudflare R2 within the time - MAX_UPLOAD_LOG_TIME 
                # Reason 1: The network performance of the node is too bad    
                # Reason 2: The code has no access to the cloud storage, or it doesn't exist             
                g_continue_node = False  # Intolerable
                print("Reallocate the node !!!!!!!!!")

            vtr_queue.put( None ) # Notify the VTR thread to stop extending the visibility timeout
            time.sleep(2)         # Ensure the VTR thread stops extending the visibility timeout
            Delete_A_Job(job) # We don't verify whether it is succeed
                              # The job should be aborted (not deleted) if the error is from the node, 
                              # because another nodes can take the job after the visibility timeout
            continue # next job or node reallocation
 
        # Now we can start
        print(f"New job: begin {g_start}, end {g_end}", flush=True)

    ######################################## Run the job - long running and interruptible
    time_start = time.perf_counter()
    
    g_abort = False 
    Reset_Upload_Error() 

    for t_step in range(g_finishedStep+1, g_end+1):

        ########## # GPU Compute: start for a specific steps
        g_tempSum = g_tempSum + t_step
        
        t_start  = time.perf_counter()
        while True:
            t_end = time.perf_counter()
            if (t_end - t_start) > step_running_time:
                break
        ########## # GPU Compute: end

        time_end = time.perf_counter()
        
        ############################################################################
        # Monitor the system: visibility timeout, network performance and errors, processing capability 
        t_vt_health = Get_Visibility_Timeout_Health()
        t_length = upload_task_queue.qsize()
        t_error = Get_Upload_Error()
        print(f"Visibility Timeout Health: {t_vt_health}, The upload error: {t_error}, The upload queue length: {t_length}")
            
        if not t_vt_health: # Other nodes have already taken the job
            g_abort = True 
            print("Abort the job execution !!!!!!")
            break
        elif t_length >= 3 or t_error > 0: # the previous uploads failed or piled up
            g_abort = True 
            g_continue_node = False
            print("Abort the job execution !!!!!!")
            print("Reallocate the node !!!!!!!!!")
            break
        # elif the processing capability is too bad (based on a reference value or prior experience)
        #   g_abort = True 
        #   g_continue_node = False
        #   print("Abort the job execution !!!!!!")
        #   print("Reallocate the node !!!!!!!!!")
        #   break
        else:
            pass
        ############################################################################

        if (time_end - time_start) < state_saving_internal: 
            continue

        # After passing the health check and the designated time, save the state
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        percentage = "{:0.2%}".format((t_step - g_start) / (g_end - g_start))
        g_logs.append(f'UTC Time: {now} - the current step: {t_step}, finished {percentage}') # Record this event

        with open(state_file, 'w') as f:  # Save the state
            temp = str(g_start) + '\n' + str(g_end) + '\n' + str(t_step) + '\n' + str(g_tempSum)
            f.write(temp)
            print(f'To save the status every {state_saving_internal} seconds: begin {g_start}, end {g_end}, t {t_step}, sum_t {g_tempSum}', flush=True)

        with open(logs_file, 'w') as f:   # Save the logs
            for item in g_logs[0:-1]:
                f.write(f"{item}\n")
            f.write(g_logs[-1])

        # Copy the data to a temp file
        state_temp_file  = os.path.join( os.path.dirname(__file__), 'data/' + str(uuid.uuid4()) )           
        shutil.copyfile(state_file, state_temp_file)
        logs_temp_file   = os.path.join( os.path.dirname(__file__), 'data/' + str(uuid.uuid4()) ) 
        shutil.copyfile(logs_file, logs_temp_file)

        # Put it into the upload queue 
        # We don't verify whether it is succeed here
        task = { "sub_tasks"  : [ { "source": logs_temp_file,  "bucket": BUCKET,  "target": FOLDER+"/logs.txt" },
                                  { "source": state_temp_file, "bucket": BUCKET,  "target": FOLDER+"/state.txt"} ],
                 "requiring_ack": False }       
        upload_task_queue.put(task) 
         
        time_start = time.perf_counter() # Update the timer for the next state saving

    if g_abort:
        vtr_queue.put( None ) # Notify the VTR thread to stop extending the visibility timeout
        time.sleep(2)         # Ensure the VTR thread stops extending the visibility timeout
        # Job Abortion: We will not delete the job from AWS SQS in this case, because it is not finished !!!
        continue # next job or node reallocation

    # The simulation is finished at this point.

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    g_logs.append(f'Machine ID: {salad_machine_id} - UTC Time: {now} - The job is done') # add this node info

    with open(output_file, 'w') as f: # Save the output: sum
        f.write(f"{g_tempSum}")
        print(f'To save the final job output: the sum of {g_start} ... {g_end} is {g_tempSum}', flush=True)
    with open(logs_file, 'w') as f:   # Save the logs
        for item in g_logs[0:-1]:
           f.write(f"{item}\n")
        f.write(g_logs[-1])

    # Copy the data to a temp file
    output_temp_file   = os.path.join( os.path.dirname(__file__), 'data/' + str(uuid.uuid4()) ) 
    shutil.copyfile(output_file, output_temp_file)
    logs_temp_file   = os.path.join( os.path.dirname(__file__), 'data/' + str(uuid.uuid4()) ) 
    shutil.copyfile(logs_file, logs_temp_file)

    # Put it into the upload queue 
    task = { "sub_tasks"  : [ { "source": output_temp_file, "bucket": BUCKET,  "target": FOLDER+"/output.txt"}, 
                              { "source": logs_temp_file,   "bucket": BUCKET,  "target": FOLDER+"/logs.txt"  } ],
             "requiring_ack": True }  
    upload_task_queue.put(task)  
        
    if Wait(ack_queue, MAX_UPLOAD_TIME) != WAITING.SUCCESS: # Blocking 
        # This is a big problem: the logs file cannot be uploaded to Cloudflare R2 within the time: 
        # Reason 1: The network performance of the node is too bad               
        # Reason 2: The code has no access to the cloud storage, or it doesn't exist             
        g_continue_node = False  # Intolerable
        
        vtr_queue.put( None ) # Notify the VTR thread to stop extending the visibility timeout
        time.sleep(2)         # Ensure the VTR thread stops extending the visibility timeout
        # Job Abortion: We will not delete the job from AWS SQS in this case, because the job is not uploaded successfully !!!
        continue # node reallocation
    
    vtr_queue.put( None ) # Notify the VTR thread to stop extending the visibility timeout
    time.sleep(2)         # Ensure the VTR thread stops extending the visibility timeout
    Delete_A_Job(job) # We don't verify whether it is succeed
    continue # next job 
 