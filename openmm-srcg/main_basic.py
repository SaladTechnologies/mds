from openmm.app import *
from openmm import *
from openmm.unit import *
import os
import time
import shutil
import boto3
from sys import stdout
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BUCKET     = os.getenv("BUCKET")
PREFIX     = os.getenv("PREFIX")
FOLDER     = os.getenv("FOLDER")
PDB_FILE   = os.getenv("PDB_FILE")  
MAX_STEPS  = int(os.getenv("MAX_STEPS"))  

BENCHMARK_STEPS = int(os.getenv("BENCHMARK_STEPS"))  

SAVING_INTERVAL_SECONDS = int(os.getenv("SAVING_INTERVAL_SECONDS")) # 1800 seconds

CLOUDFLARE_ID             = os.getenv("CLOUDFLARE_ID", "")
CLOUDFLARE_KEY            = os.getenv("CLOUDFLARE_KEY", "")
CLOUDFLARE_ENDPOINT_URL   = os.getenv("CLOUDFLARE_ENDPOINT_URL", "")

LOCAL_FOLDER = "local"
if os.path.exists(LOCAL_FOLDER):
    shutil.rmtree(LOCAL_FOLDER)
os.makedirs(LOCAL_FOLDER)

PDB_LOCAL      = os.path.join(LOCAL_FOLDER, PDB_FILE)               # local: LOCAL_FOLDER/xxx.pdb

CPT_FILE       = f"checkpoint.chk"                                  # cloud: checkpoint.chk
CPT_LOCAL      = os.path.join(LOCAL_FOLDER, CPT_FILE)               # local: LOCAL_FOLDER/checkpoint.chk

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
    

def main():

    g_start = time.perf_counter()

    # Download the input PDB 
    s3_key =  "/".join([PREFIX, FOLDER, PDB_FILE]) 
    if not s3_download(S3_CLIENT, BUCKET, s3_key, PDB_LOCAL):
        print(f"Failed to download input PDB file {BUCKET}/{s3_key}. Exiting.")
        os._exit(1)

    # ========= Setup =========
    pdb = PDBFile(PDB_LOCAL)
    forcefield = ForceField('amber14-all.xml', 'amber14/tip3pfb.xml')
    system = forcefield.createSystem(pdb.topology, nonbondedMethod=PME, nonbondedCutoff=1*nanometer, constraints=HBonds)
    integrator = LangevinMiddleIntegrator(300*kelvin, 1/picosecond, 0.004*picoseconds)
    simulation = Simulation(pdb.topology, system, integrator)

    # Download checkpoint if exists
    s3_key =  "/".join([PREFIX, FOLDER, CPT_FILE])
    cpt_exists = s3_download(S3_CLIENT, BUCKET, s3_key, CPT_LOCAL)
    if cpt_exists: # load it and check the step count
        with open(CPT_LOCAL, 'rb') as f:
            simulation.context.loadCheckpoint(f.read())
        steps_done = simulation.context.getState().getStepCount() # Total cumulative step count
        if steps_done >= MAX_STEPS:
            print(f"Checkpoint file {CPT_LOCAL} indicates that the simulation is already completed with {steps_done} steps. Exiting.")
            os._exit(0)  
        else: #
            print(f"Checkpoint file {CPT_LOCAL} found. Resuming from step {steps_done}.")  
    else:
        steps_done = 0 # Start from scratch if no checkpoint
        simulation.context.setPositions(pdb.positions)
        simulation.minimizeEnergy()

    # ========= Dynamic Benchmark =========
    if MAX_STEPS - steps_done > BENCHMARK_STEPS:
        print(f"Benchmarking node performance with {BENCHMARK_STEPS} steps...")
        start_bench = time.time()
        simulation.step(BENCHMARK_STEPS) # Benchmarking, not reporting
        end_bench = time.time()
        time_per_step = (end_bench - start_bench) / BENCHMARK_STEPS
        print(f"Estimated time per step: {time_per_step:.4f} seconds")
        
        # ========= Calculate chunk_steps for SAVING_INTERVAL_SECONDS =========
        chunk_steps = int(SAVING_INTERVAL_SECONDS  / time_per_step) 
        print(f"Taking {SAVING_INTERVAL_SECONDS} seconds to run a chunk of {chunk_steps} steps.")

        # Can be removed
        # steps_done = simulation.context.getState().getStepCount() # as ENCHMARK_STEPS is performed

    # ========= Run chunks until completion =========
    while True:

        steps_done = simulation.context.getState().getStepCount()  # Total cumulative step count

        if steps_done >= MAX_STEPS:
            print(f"The simulation is completed with {steps_done} steps.")
            break

        if MAX_STEPS - steps_done <= chunk_steps:
            chunk_steps = MAX_STEPS - steps_done  # Adjust to remaining steps
            
        chunk_id = steps_done + chunk_steps

        # ========= Reporters (new files per chunk) =========
        # Clear previous reporters to avoid conflicts
        simulation.reporters.clear()

        OUTPUT_DCD_FILE = f'output_{chunk_id}.dcd'
        OUTPUT_DCD_FILE_LOCAL = os.path.join(LOCAL_FOLDER, OUTPUT_DCD_FILE)
        LOG_FILE = f'log_{chunk_id}.txt'
        LOG_FILE_LOCAL = os.path.join(LOCAL_FOLDER, LOG_FILE)

        # Decide how many data points saved in each chunk file: log, dcd
        # Adjust reporting frequency based on chunk size
        report_freq = min(1000, chunk_steps)  # At least 1, at most 1000, aim for ~10 reports
        simulation.reporters.append(DCDReporter(OUTPUT_DCD_FILE_LOCAL, report_freq))
        simulation.reporters.append(StateDataReporter(LOG_FILE_LOCAL, report_freq, step=True, potentialEnergy=True, temperature=True))

        start_time = time.time()
        print(f"---------> Running simulation chunk {chunk_id}...")
        simulation.step(chunk_steps)
        print(f"---------> Completed simulation chunk {chunk_id}.  ")

        # ========= Save checkpoint =========
        with open(CPT_LOCAL, 'wb') as f:
            f.write(simulation.context.createCheckpoint())

        # ========= Upload checkpoint and per-chunk outputs =========
        s3_key =  "/".join([PREFIX, FOLDER, OUTPUT_DCD_FILE])
        s3_upload(S3_CLIENT, BUCKET, OUTPUT_DCD_FILE_LOCAL, s3_key)
    
        s3_key =  "/".join([PREFIX, FOLDER, LOG_FILE])
        s3_upload(S3_CLIENT, BUCKET, LOG_FILE_LOCAL, s3_key)

        s3_key =  "/".join([PREFIX, FOLDER, CPT_FILE])
        s3_upload(S3_CLIENT, BUCKET, CPT_LOCAL, s3_key)

    g_end = time.perf_counter()
    print( "The simulation runtime was {:.3f} seconds".format(g_end - g_start) )  


if __name__ == "__main__":
    main()