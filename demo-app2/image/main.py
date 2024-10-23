from config import Retrieve_A_Job, Uploader
from config import s3
import os
import time
import queue
import threading
import shutil
import uuid


# Initial check: CUDA Version, VRAM and others
# Network test: latency to some location and bandwidth
# Trigger reallocation here if a node is not suitable: http://169.254.169.254/v1/reallocate
# https://docs.salad.com/products/sce/container-groups/imds/imds-reallocate
# The instance only run a few seconds to do the initial check, so additional costs for doing this could be ignored.


# If run the container locally, use the random ID
salad_machine_id = os.getenv("SALAD_MACHINE_ID", str(uuid.uuid4()) )


VISIBILITY_TIMEOUT = 120 # 120 seconds, the visibility timeout setting in AWS SQS

MAX_RUNNING_TIME   =  60 #  60 seconds
# If takes more than this, stop processing this job;
# After visibility times out, other instances would retrieve this job again and continue the job execution.


input_file  = os.path.join( os.path.dirname(__file__), 'data/input.txt'   ) # input
state_file  = os.path.join( os.path.dirname(__file__), 'data/state.txt'   ) # state
logs_file   = os.path.join( os.path.dirname(__file__), 'data/logs.txt'    ) # logs
output_file = os.path.join( os.path.dirname(__file__), 'data/output.txt' )  # output


# The main thread sends the uploading tasks to the queue
uploading_task_queue = queue.Queue()
# The ul thread finishes the uploading tasks and removes the temp files
# It may delete the job from the AWS SQS if the final output is uploaded
ul_thread = threading.Thread(target=Uploader, args=(uploading_task_queue,))
ul_thread.start()


while True:

    print("The uploading queue length: {}".format(uploading_task_queue.qsize()), flush=True)
    # Monitor the network performance here. 
    # If many uploading tasks are waiting, you can do something (wait for a whie and then quit - trigger reallocation) 

    print("Retrieving ......", flush=True)

    jobs = Retrieve_A_Job(WAIT_TIME=5)  # Block here; will exit with non-zero if sth goes wrong, triggering reallocation
    if len(jobs) == 0:
        continue

    job = jobs[0] 
    print("Retrieved a job: "+ job[0]['folder'], flush=True)

    BUCKET                = job[0]['bucket']
    FOLDER                = job[0]['folder'] 
    state_saving_internal = float(job[0]['parameters']['STATE_SAVING_INTERVAL'])
    step_running_time     = float(job[0]['parameters']['STEP_RUNNING_TIME'])

    gloal_time_start = time.perf_counter()

    ######################################## Remove the previous job data
    files = [input_file, state_file, logs_file, output_file]
    for file in files:
        if os.path.exists( file ):
            os.remove( file)
            
    ######################################## Download the input
    # Read the job input: start and end

    try:
        s3.download_file(BUCKET, FOLDER+"/input.txt", input_file ) # Download from Cloud Storage
        with open(input_file, 'r') as f:
            g_Start, g_End = f.read().splitlines()
            g_Start, g_End = int(g_Start), int(g_End)
    except Exception as e: # no file, no permission...
        print(str(e)) 
        print('no input', flush=True)

        with open(logs_file, 'w') as f:   # Save the logs
            f.write(f'{salad_machine_id} no input')
        logs_temp_file   = os.path.join( os.path.dirname(__file__), 'data/' + str(uuid.uuid4()) ) 
        shutil.copyfile(logs_file, logs_temp_file)
        task = { "sub_tasks"  : [ { "source": logs_temp_file,   "bucket": BUCKET,  "target": FOLDER+"/logs.txt" } ],
                 "msg_handler": job[1] }     
        uploading_task_queue.put(task)         

        continue

    # Handle the exception
    if g_Start > g_End:
        print('ERROR - wrong input', flush=True)

        with open(logs_file, 'w') as f:   # Save the logs
            f.write(f'{salad_machine_id} wrong input')
        logs_temp_file   = os.path.join( os.path.dirname(__file__), 'data/' + str(uuid.uuid4()) ) 
        shutil.copyfile(logs_file, logs_temp_file)
        task = { "sub_tasks"  : [ { "source": logs_temp_file,   "bucket": BUCKET,  "target": FOLDER+"/logs.txt" } ],
                 "msg_handler": job[1] }     
        uploading_task_queue.put(task)            

        continue 

    print(f'The job is to calculate the sum of {g_Start} ... {g_End}', flush=True)

    ######################################## Download and resume the state
    g_logs = []
    is_New_Job = True
    g_finishedStep = g_Start - 1
    g_tempSum = 0

    try:
        s3.download_file(BUCKET, FOLDER+"/state.txt", state_file )
        s3.download_file(BUCKET, FOLDER+"/logs.txt", logs_file )
        is_New_Job = False
    except Exception as e:
        # print(str(e)) 
        print("No state and logs files", flush=True)
        pass
    
    if not is_New_Job:
        with open(logs_file, 'r') as f:
            for temp in f.read().splitlines():
                g_logs.append(temp)
        with open(state_file, 'r') as f:
            g_finishedStep, g_tempSum = f.read().splitlines()
            g_finishedStep, g_tempSum = int(g_finishedStep), int(g_tempSum)
            print(f"Unfinished job, resume from the previous state: the sum of {g_Start} ... {g_finishedStep} is {g_tempSum}", flush=True)
    else:
        print("New job, start from scratch", flush=True)

    ######################################## Run the job - long running and interruptible
    Timeout = False
    time_start = time.perf_counter()
    for x in range(g_finishedStep+1, g_End+1):

        g_tempSum = g_tempSum + x
        time.sleep(step_running_time)
        time_end = time.perf_counter()

        if (time_end - time_start) > state_saving_internal:

            g_logs.append(f'{salad_machine_id} {x}') # Record this event

            with open(state_file, 'w') as f:  # Save the state: t and sum_t
                temp = str(x) + '\n' + str(g_tempSum)
                f.write(temp)
                print(f'To save the status every {state_saving_internal} seconds: the sum of {g_Start} ... {x} is {g_tempSum}', flush=True)
            with open(logs_file, 'w') as f:   # Save the logs
                for item in g_logs[0:-1]:
                    f.write(f"{item}\n")
                f.write(g_logs[-1])

            # Copy the data to a temp file
            state_temp_file  = os.path.join( os.path.dirname(__file__), 'data/' + str(uuid.uuid4()) )           
            #print(state_file, " -> ",state_temp_file, flush=True)
            shutil.copyfile(state_file, state_temp_file)

            # Copy the data to a temp file
            logs_temp_file   = os.path.join( os.path.dirname(__file__), 'data/' + str(uuid.uuid4()) ) 
            #print(logs_file, " -> ",logs_temp_file, flush=True)
            shutil.copyfile(logs_file, logs_temp_file)

            task = { "sub_tasks"  : [ { "source": state_temp_file, "bucket": BUCKET,  "target": FOLDER+"/state.txt"},
                                      { "source": logs_temp_file,  "bucket": BUCKET,  "target": FOLDER+"/logs.txt" } ],
                     "msg_handler": None  }        
            uploading_task_queue.put(task) 
            
            # Update the timer for saving state
            time_start = time.perf_counter()

            # Check the running time after saving the state 
            gloal_time_end = time.perf_counter()
            if (gloal_time_end - gloal_time_start) >= MAX_RUNNING_TIME:
                Timeout = True
                print(f'Stop processing this job and allow it time out', flush=True)
                break # Process next job


    if Timeout == True:
        continue # Process next job

    # The job is finished while running to this point

    # Record this event, there might be some addtional steps after the last saveing state
    g_logs.append(f'{salad_machine_id} {x}') 
  
    with open(output_file, 'w') as f: # Save the output: sum
        f.write(f"{g_tempSum}")
        print(f'To save the job output: the sum of {g_Start} ... {g_End} is {g_tempSum}', flush=True)
    with open(logs_file, 'w') as f:   # Save the logs
        for item in g_logs[0:-1]:
            f.write(f"{item}\n")
        f.write(g_logs[-1])

    output_temp_file   = os.path.join( os.path.dirname(__file__), 'data/' + str(uuid.uuid4()) ) 
    # print(output_file, " -> ",output_temp_file, flush=True)
    shutil.copyfile(output_file, output_temp_file)

    logs_temp_file   = os.path.join( os.path.dirname(__file__), 'data/' + str(uuid.uuid4()) ) 
    # print(logs_file, " -> ",logs_temp_file, flush=True)
    shutil.copyfile(logs_file, logs_temp_file)

    task = { "sub_tasks"  : [ { "source": output_temp_file, "bucket": BUCKET,  "target": FOLDER+"/output.txt"},
                              { "source": logs_temp_file,   "bucket": BUCKET,  "target": FOLDER+"/logs.txt" } ],
             "msg_handler": job[1] }     
       
    uploading_task_queue.put(task)         
