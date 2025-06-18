import os
import time
import subprocess
import shutil
import os
import boto3
from datetime import datetime
import glob
import re
from dotenv import load_dotenv

load_dotenv()

# BUCKER/PREFIX/FOLDER/INPUT_TPR (xxx.tpr) 
BUCKET     = os.getenv("BUCKET")
PREFIX     = os.getenv("PREFIX")
FOLDER     = os.getenv("FOLDER")
TPR_FILE   = os.getenv("TPR_FILE")  
MAX_STEPS  = int(os.getenv("MAX_STEPS"))  
SAVING_INTERVAL_HOURS = os.getenv("SAVING_INTERVAL_HOURS") 

CLOUDFLARE_ID             = os.getenv("CLOUDFLARE_ID", "")
CLOUDFLARE_KEY            = os.getenv("CLOUDFLARE_KEY", "")
CLOUDFLARE_ENDPOINT_URL   = os.getenv("CLOUDFLARE_ENDPOINT_URL", "")

LOCAL_FOLDER = "local"
if os.path.exists(LOCAL_FOLDER):
    shutil.rmtree(LOCAL_FOLDER)
os.makedirs(LOCAL_FOLDER)

BASE_NAME      = os.path.splitext(os.path.basename(TPR_FILE))[0]    # xxx.tpr -> xxx

CPT_FILE       = f"{BASE_NAME}.cpt"                                 # cloud: xxx.cpt
CPT_LOCAL      = os.path.join(LOCAL_FOLDER, CPT_FILE)               # local: LOCAL_FOLDER/xxx.cpt

CPT_PREV_FILE  = f"{BASE_NAME}_prev.cpt"                            # cloud: xxx_prev.cpt
CPT_PREV_LOCAL = os.path.join(LOCAL_FOLDER, CPT_PREV_FILE)          # local: LOCAL_FOLDER/xxx_prev.cpt

TPR_LOCAL      = os.path.join(LOCAL_FOLDER, TPR_FILE)               # local: LOCAL_FOLDER/xxx.tpr

DEFFNM         = os.path.join(LOCAL_FOLDER, BASE_NAME)              # local: LOCAL_FOLDER/xxx
PATTERN        = os.path.join(LOCAL_FOLDER, f"{BASE_NAME}.part*.*") # local: LOCAL_FOLDER/xxx.part*.*

S3_CLIENT = boto3.client(
    "s3",
    endpoint_url=CLOUDFLARE_ENDPOINT_URL,
    aws_access_key_id=CLOUDFLARE_ID,
    aws_secret_access_key=CLOUDFLARE_KEY,
    region_name="auto",
)

def s3_download(s3client, bucket, key, local_path):
    try:
        print(f"Downloading {bucket}/{key} to {local_path}")
        s3client.download_file(bucket, key, local_path)
        return True
    except Exception as e:
        print(f"Failed to download {bucket}/{key} to {local_path}: {e}")
        return False

def s3_upload(s3client, bucket, local_path, key):
    try:
        print(f"Uploading {local_path} to {bucket}/{key}")
        if os.path.exists(local_path):
            s3client.upload_file(local_path, bucket, key)
        return True
    except Exception as e:
        print(f"Failed to upload {local_path} to {bucket}/{key}: {e}")
        return False
    
def find_new_files(pattern, before_set):
    after_set = set(glob.glob(pattern))
    return list(after_set - before_set)

def get_steps_from_cpt(cpt_file):
    try:
        result = subprocess.run( ["gmx", "dump", "-cp", cpt_file], capture_output=True, text=True, check=True)
        for line in result.stdout.splitlines():
            m = re.search(r'step\s*=\s*(\d+)', line) # None if no match is found
            if m: # if m is not None
                return int(m.group(1))
    except Exception as e:
        print(f"Error processing checkpoint file {cpt_file}: {e}") 
    return None

def main():

    g_start = time.perf_counter()

    # Download the input TPR 
    s3_key =  "/".join([PREFIX, FOLDER, TPR_FILE]) 
    if not s3_download(S3_CLIENT, BUCKET, s3_key, TPR_LOCAL):
        print(f"Failed to download input TPR file {BUCKET}/{s3_key}. Exiting.")
        os._exit(1)

    steps_done = 0

    # Download checkpoint if exists
    s3_key =  "/".join([PREFIX, FOLDER, CPT_FILE])
    cpt_exists = s3_download(S3_CLIENT, BUCKET, s3_key, CPT_LOCAL)

    # Check if checkpoint exists and is valid, and get the number of steps done
    if cpt_exists:
        steps_done = get_steps_from_cpt(CPT_LOCAL) # Also act as a check 
        if steps_done is None: 
            # If the cpt file is corrupted, the simulation should halt to allow investigation. 
            # Proceeding could result in overwriting previously generated data.
            print(f"Checkpoint file {CPT_LOCAL} is corrupted or not valid. Exiting.")
            os._exit(1) # Need investigation.
        elif steps_done >= MAX_STEPS:
            print(f"Checkpoint file {CPT_LOCAL} indicates that the simulation is already completed with {steps_done} steps. Exiting.")
            os._exit(0)
        else: #
            print(f"Checkpoint file {CPT_LOCAL} found. Resuming from step {steps_done}.")

    while True:  

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

        # print(base_cmd)

        before_files = set(glob.glob(PATTERN)) # Record existing files before running mdrun
        try:
            print("\n" + "-" * 60 + " start")
            subprocess.run(base_cmd, check=True)
            print("-" * 60 + " end\n")
            print("Command ran successfully!")
        except subprocess.CalledProcessError as e: 
            print("-" * 60 + " error\n")
            print(f"Command failed with exit code {e.returncode}")
            os._exit(1) # Need investigation.
        new_files = find_new_files(PATTERN, before_files) # Find new files generated by mdrun

        # There must be a cpt file when gmx mdrun stops properly
        cpt_exists = True

        # Upload new files - trr, edr, log, xtc(optional), gro(final)
        for file_path in new_files:
            s3_key =  "/".join([PREFIX, FOLDER, os.path.basename(file_path)])
            s3_upload(S3_CLIENT, BUCKET, file_path, s3_key)        
        
        # Then upload latest and previous checkpoint if present
        if os.path.exists(CPT_LOCAL):
            s3_key =  "/".join([PREFIX, FOLDER, CPT_FILE])
            s3_upload(S3_CLIENT, BUCKET, CPT_LOCAL, s3_key)
        if os.path.exists(CPT_PREV_LOCAL):
            s3_key =  "/".join([PREFIX, FOLDER, CPT_PREV_FILE])
            s3_upload(S3_CLIENT, BUCKET, CPT_PREV_FILE, s3_key)

        steps_done = get_steps_from_cpt(CPT_LOCAL) # Also act as a check to the checkpoint file 
     
        if steps_done is None:
            # If the cpt file is corrupted, the simulation should halt to allow investigation. 
            # Proceeding could result in overwriting previously generated data.
            print(f"Checkpoint file {CPT_LOCAL} is corrupted or not valid. Exit. ")
            os._exit(1) # Need investigation.
        elif steps_done >= MAX_STEPS:
            print(f"The simulation is completed with {steps_done} steps.")
            break
        else:
            print(f"Steps done: {steps_done}, continue ...")


    g_end = time.perf_counter()
    print( "The simulation runtime was {:.3f} seconds".format(g_end - g_start) )  

if __name__ == "__main__":
    main()