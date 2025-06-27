import os
import time
import subprocess
import shutil
import os
import boto3
from datetime import datetime
import uuid
import queue
import threading
import glob
import re
from dotenv import load_dotenv
from helper import Find_New_Files, Get_Steps_From_Cpt, Downloader_Chunked_Parallel, \
                   Reallocate, Shutdown_SRCG, \
                   History_Initialize, History_Record, \
                   Notify_Uploader, Upload_Health_Check, Wait_For_Upload_Completion, Uploader

load_dotenv()

# Support both: BUCKER/PREFIX/FOLDER/INPUT_TPR (xxx.tpr), BUCKER/FOLDER/INPUT_TPR (xxx.tpr) 
BUCKET     = os.getenv("BUCKET")
PREFIX     = os.getenv("PREFIX","")  # Optional, can be empty
FOLDER     = os.getenv("FOLDER")
TPR_FILE   = os.getenv("TPR_FILE")  
MAX_STEPS  = int(os.getenv("MAX_STEPS",'0'))  
SAVING_INTERVAL_HOURS = os.getenv("SAVING_INTERVAL_HOURS",'0.5') 

# if not provided, wait forever to keep the SRCG running on SaladCloud
if not BUCKET or not FOLDER or not TPR_FILE or MAX_STEPS==0:
    while True:
        print("No input file, sleep infinity ......", flush=True)
        time.sleep(10)

LOCAL_FOLDER = "local" # FOLDER, or use the same folder name as the cloud folder
if os.path.exists(LOCAL_FOLDER):
    shutil.rmtree(LOCAL_FOLDER)
os.makedirs(LOCAL_FOLDER)

# Buffer folder for uploading files
UPLOAD_FOLDER = "uploading"
if os.path.exists(UPLOAD_FOLDER):
    shutil.rmtree(UPLOAD_FOLDER)
os.makedirs(UPLOAD_FOLDER)

BASE_NAME      = os.path.splitext(os.path.basename(TPR_FILE))[0]    # xxx.tpr -> xxx
CPT_FILE       = f"{BASE_NAME}.cpt"                                 # cloud: xxx.cpt
CPT_LOCAL      = os.path.join(LOCAL_FOLDER, CPT_FILE)               # local: LOCAL_FOLDER/xxx.cpt
CPT_PREV_FILE  = f"{BASE_NAME}_prev.cpt"                            # cloud: xxx_prev.cpt
CPT_PREV_LOCAL = os.path.join(LOCAL_FOLDER, CPT_PREV_FILE)          # local: LOCAL_FOLDER/xxx_prev.cpt
TPR_LOCAL      = os.path.join(LOCAL_FOLDER, TPR_FILE)               # local: LOCAL_FOLDER/xxx.tpr
DEFFNM         = os.path.join(LOCAL_FOLDER, BASE_NAME)              # local: LOCAL_FOLDER/xxx
PATTERN        = os.path.join(LOCAL_FOLDER, f"{BASE_NAME}.part*.*") # local: LOCAL_FOLDER/xxx.part*.*, to capture new files after each run

HISTORY_FILE   = 'history.txt'                                      # cloud: to keep the history of the simulation, nodes and steps 
HISTORY_LOCAL  = os.path.join(LOCAL_FOLDER, HISTORY_FILE)           # local: LOCAL_FOLDER/history.txt

def main():

    g_start = time.perf_counter()

    # Sync Download: the history info, including nodes and steps, for better visibility on SaladCloud
    result = Downloader_Chunked_Parallel('dl_history', BUCKET, PREFIX, FOLDER, HISTORY_FILE, HISTORY_LOCAL, "10M", "10")
    print(result)  

    temp =  FOLDER + "/" + TPR_FILE + "_" + str(MAX_STEPS) + "_steps" 
    History_Initialize(HISTORY_LOCAL, temp) # Initialize from the history file or scratch if not exists

    steps_done = 0
    cpt_exists = False

    # Sync Download: the input TPR 
    result = Downloader_Chunked_Parallel('dl_tpr', BUCKET, PREFIX, FOLDER, TPR_FILE, TPR_LOCAL, "10M", "10")
    if len(result) <= 1:
        print(f"Failed to download input TPR file {BUCKET}/{PREFIX}/{FOLDER}/{TPR_FILE}.")
        Shutdown_SRCG() # Need investigation.
    else:
        print(result)  

    # Sync Download: the checkpoint, may encounter the NoFoundError if it does not exist
    result = Downloader_Chunked_Parallel('dl_cpt', BUCKET, PREFIX, FOLDER, CPT_FILE, CPT_LOCAL, "10M", "10")
    print(result)
    if len(result) > 1:
        cpt_exists = True

    # Check if the checkpoint exists and is valid, and get the number of steps done
    if cpt_exists:
        steps_done = Get_Steps_From_Cpt(CPT_LOCAL) # Also act as a check 
        if steps_done is None: 
            # If the cpt file is corrupted, the simulation should halt to allow investigation. 
            # Proceeding could result in overwriting previously generated data.
            print(f"Checkpoint file {CPT_LOCAL} is corrupted or not valid.")
            Shutdown_SRCG() # Need investigation.
        elif steps_done >= MAX_STEPS:
            print(f"Checkpoint file {CPT_LOCAL} indicates that the simulation is already completed with {steps_done} steps.")
            Shutdown_SRCG()
        else: #
            print(f"Checkpoint file {CPT_LOCAL} found. Resuming from step {steps_done}.")

    # The access to cloud storage should be good at this point
    task_queue = queue.Queue()
    ul_thread = threading.Thread(target=Uploader, args=(task_queue,))
    ul_thread.start()

    History_Initialize(HISTORY_LOCAL, 'START') # Record the start of the task

    task_completed = False
    while True:  

        result = Upload_Health_Check()
        print(f"\nUpload Health Check: {result}")
        if result['failure'] > 0 or result['waiting'] > 10 or result['average_throughput_Mbps'] < 10:
            print("Upload health check failed, changing a node ...")
            # The generated files in the queue will not be uploaded
            Reallocate("network performance issue")

        # Prepare mdrun command
        base_cmd = [
            "gmx", "mdrun",
            "-nb", "gpu", "-pme", "gpu", "-bonded", "gpu", "-update", "gpu",
            "-ntmpi", "1", "-ntomp", "8", "-pin", "on", "-pinstride", "1",
            "-noappend",
            "-s", TPR_LOCAL,
            "-deffnm", os.path.join(LOCAL_FOLDER, BASE_NAME),
            "-nsteps", str(MAX_STEPS - steps_done),
            "-maxh", SAVING_INTERVAL_HOURS
        ]
        if cpt_exists:
            base_cmd += ["-cpi", CPT_LOCAL]

        before_files = set(glob.glob(PATTERN)) # Record existing files before running mdrun
        try:
            print("\nExecuting: " + ' '.join(base_cmd))
            subprocess.run(base_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            #subprocess.run(base_cmd, check=True)
            print("Command ran successfully!")
        except subprocess.CalledProcessError as e: 
            print(f"Command failed with exit code {e.returncode}")
            # The generated files from this run will not be uploaded
            break # aborted,  need investigation.
        new_files = Find_New_Files(PATTERN, before_files) # Find new files generated by mdrun

        # There must be an cpt file (or its updated version) when gmx mdrun stops properly
        cpt_exists = True

        old_steps_done = steps_done

        steps_done = Get_Steps_From_Cpt(CPT_LOCAL) # Also act as a check 
        if steps_done is None:
            # If the cpt file is corrupted, the simulation should halt to allow investigation. 
            # Proceeding could result in overwriting previously generated data.
            print(f"Checkpoint file {CPT_LOCAL} is corrupted or not valid.")
            # The generated files from this run will not be uploaded
            break # aborted, need investigation.
        elif steps_done >= MAX_STEPS:
            print(f"The simulation is completed with {steps_done} steps.")
            task_completed = True    
        else:
            print(f"Steps done: {steps_done}, continue ...")

        History_Record(HISTORY_LOCAL, steps_done - old_steps_done, steps_done, MAX_STEPS, task_completed)

        UID = str(uuid.uuid4()) + "-"

        # Async Upload: new files - trr, edr, log, xtc(optional), gro(final)
        for file_path in new_files:
            tempFile = os.path.join(UPLOAD_FOLDER, UID + os.path.basename(file_path))
            shutil.copy(file_path, tempFile) # Make a copy
            message = { 'task': f'ul_{file_path.split(".")[-1]}',  # Get the file extension
                        'source': tempFile, 'bucket': BUCKET, 'prefix': PREFIX, 'folder': FOLDER, 'target': os.path.basename(file_path),
                        'chunk_size_mbtype': "10M", 'concurrency': "10" }
            Notify_Uploader(task_queue, message) # 
        
        # Async Upload: latest checkpoint and previous checkpoint if present
        for local_path, file_name, task_name in [ (CPT_LOCAL,      CPT_FILE,      'ul_cpt'), 
                                                  (CPT_PREV_LOCAL, CPT_PREV_FILE, 'ul_prev_cpt'),
                                                  (HISTORY_LOCAL, HISTORY_FILE,   'ul_history') ]:
            if not os.path.exists(local_path):
                continue
            temp_file = os.path.join(UPLOAD_FOLDER, UID + file_name) # avoid the conflict with the previous one
            shutil.copy(local_path, temp_file) # Make a copy
            message = { 'task': task_name, 
                        'source': temp_file, 'bucket': BUCKET, 'prefix': PREFIX, 'folder': FOLDER, 'target': file_name,
                        'chunk_size_mbtype': "10M", 'concurrency': "10" }
            Notify_Uploader(task_queue, message)  

        if task_completed == True:
            break


    g_end = time.perf_counter()
    print( "The runtime was {:.3f} seconds".format(g_end - g_start) )  

    Wait_For_Upload_Completion(task_queue)
    Shutdown_SRCG()

if __name__ == "__main__":
    main()

