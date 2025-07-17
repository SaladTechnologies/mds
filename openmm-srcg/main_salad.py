from openmm.app import *
from openmm import *
from openmm.unit import *
import os
import time
import shutil
import uuid
import queue
import threading
from sys import stdout
from dotenv import load_dotenv
from helper import Downloader_Chunked_Parallel, \
                   Reallocate, Shutdown_SRCG, \
                   History_Initialize, History_Record, \
                   Notify_Uploader, Upload_Health_Check, Wait_For_Upload_Completion, Uploader

load_dotenv()

BUCKET     = os.getenv("BUCKET")
PREFIX     = os.getenv("PREFIX")
FOLDER     = os.getenv("FOLDER")
PDB_FILE   = os.getenv("PDB_FILE")  
MAX_STEPS  = int(os.getenv("MAX_STEPS",'0'))  
BENCHMARK_STEPS = int(os.getenv("BENCHMARK_STEPS",'10'))  
REPORT_FREQ     = int(os.getenv("REPORT_FREQ",'1000'))  # Frequency of reporting, default to 1000
SAVING_INTERVAL_SECONDS = int(os.getenv("SAVING_INTERVAL_SECONDS",'1800')) # 1800 seconds

# if not provided, wait forever to keep the SRCG running on SaladCloud
if not BUCKET or not FOLDER or not PDB_FILE or MAX_STEPS==0:
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

PDB_LOCAL      = os.path.join(LOCAL_FOLDER, PDB_FILE)               # local: LOCAL_FOLDER/xxx.pdb
CPT_FILE       = f"checkpoint.chk"                                  # cloud: checkpoint.chk
CPT_LOCAL      = os.path.join(LOCAL_FOLDER, CPT_FILE)               # local: LOCAL_FOLDER/checkpoint.chk

HISTORY_FILE   = 'history.txt'                                      # cloud: to keep the history of the simulation, nodes and steps 
HISTORY_LOCAL  = os.path.join(LOCAL_FOLDER, HISTORY_FILE)           # local: LOCAL_FOLDER/history.txt

def main():

    g_start = time.perf_counter()

    # Sync Download: the history info, including nodes and steps, for better visibility on SaladCloud
    result = Downloader_Chunked_Parallel('dl_history', BUCKET, PREFIX, FOLDER, HISTORY_FILE, HISTORY_LOCAL, "10M", "10")
    print(result)  

    temp =  FOLDER + "/" + PDB_FILE + "_" + str(MAX_STEPS) + "_steps" 
    History_Initialize(HISTORY_LOCAL, temp) # Initialize from the history file or scratch if not exists

    # Sync Download: the input PBR 
    result = Downloader_Chunked_Parallel('dl_pbr', BUCKET, PREFIX, FOLDER, PDB_FILE, PDB_LOCAL, "10M", "10")
    if len(result) <= 1:
        print(f"Failed to download input TPR file {BUCKET}/{PREFIX}/{FOLDER}/{PDB_FILE}.")
        Shutdown_SRCG() # Need investigation.
    else:
        print(result)  

    # ========= Setup =========
    pdb = PDBFile(PDB_LOCAL)
    forcefield = ForceField('amber14-all.xml', 'amber14/tip3pfb.xml')
    system = forcefield.createSystem(pdb.topology, nonbondedMethod=PME, nonbondedCutoff=1*nanometer, constraints=HBonds)
    integrator = LangevinMiddleIntegrator(300*kelvin, 1/picosecond, 0.004*picoseconds)
    simulation = Simulation(pdb.topology, system, integrator)

    steps_done = old_steps_done = 0
    cpt_exists = False

    # Sync Download: the checkpoint, may encounter the NoFoundError if it does not exist
    result = Downloader_Chunked_Parallel('dl_cpt', BUCKET, PREFIX, FOLDER, CPT_FILE, CPT_LOCAL, "10M", "10")
    print(result)
    if len(result) > 1:
        cpt_exists = True

    if cpt_exists: # load it and check the step count
        with open(CPT_LOCAL, 'rb') as f:
            simulation.context.loadCheckpoint(f.read()) # local the checkpoint file into the simulation context
        steps_done = old_steps_done = simulation.context.getState().getStepCount() # total cumulative step count
        if steps_done >= MAX_STEPS:
            print(f"Checkpoint file {CPT_LOCAL} indicates that the simulation is already completed with {steps_done} steps.")
            Shutdown_SRCG()
        else: #
            print(f"Checkpoint file {CPT_LOCAL} found. Resuming from step {steps_done}.")  
    else:
        steps_done = old_steps_done = 0# Start from scratch if no checkpoint
        old_steps_done = steps_done
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
         
        # update the steps_done after the dynamic benchmark 
        steps_done = simulation.context.getState().getStepCount() # as ENCHMARK_STEPS is performed

    # The access to cloud storage should be good at this point
    task_queue = queue.Queue()
    ul_thread = threading.Thread(target=Uploader, args=(task_queue,))
    ul_thread.start()

    History_Initialize(HISTORY_LOCAL, 'START') # Record the actual start time of simulation

    task_completed = False
    while True:

        result = Upload_Health_Check()
        print(f"\nUpload Health Check: {result}")
        if result['failure'] > 0 or result['waiting'] > 10 or result['average_throughput_Mbps'] < 10:
            print("Upload health check failed, changing a node ...")
            # The generated files in the queue will not be uploaded
            Reallocate("network performance issue")

        # if the remaining steps are less than chunk_steps, set chunk_steps to the remaining steps
        if MAX_STEPS - steps_done <= chunk_steps:
            chunk_steps = MAX_STEPS - steps_done 
            
        chunk_id = steps_done + chunk_steps # <------- chunk_id |

        # ========= Reporters (new files per chunk) =========
        # Clear previous reporters to avoid conflicts
        simulation.reporters.clear()

        OUTPUT_DCD_FILE = f'output_{chunk_id:012}.dcd'
        OUTPUT_DCD_FILE_LOCAL = os.path.join(LOCAL_FOLDER, OUTPUT_DCD_FILE)
        LOG_FILE = f'log_{chunk_id:012}.txt'
        LOG_FILE_LOCAL = os.path.join(LOCAL_FOLDER, LOG_FILE)

        # Decide how many data points saved in each chunk file: log, dcd
        # Adjust reporting frequency based on chunk size
        report_freq = min(REPORT_FREQ, chunk_steps)  # Ensure at least one report per chunk
        simulation.reporters.append(DCDReporter(OUTPUT_DCD_FILE_LOCAL, report_freq))
        simulation.reporters.append(StateDataReporter(LOG_FILE_LOCAL, report_freq, step=True, potentialEnergy=True, temperature=True))

        print(f"---------> Running simulation chunk {chunk_id}...")
        simulation.step(chunk_steps)
        print(f"---------> Completed simulation chunk {chunk_id}.  ")

        # Save checkpoint 
        with open(CPT_LOCAL, 'wb') as f:
            f.write(simulation.context.createCheckpoint())

        steps_done = simulation.context.getState().getStepCount()  # Total cumulative step count
        if steps_done >= MAX_STEPS:
            print(f"The simulation is completed with {steps_done} steps.")
            task_completed = True    
        else:
            print(f"Steps done: {steps_done}, continue ...")

        History_Record(HISTORY_LOCAL, steps_done - old_steps_done, steps_done, MAX_STEPS, task_completed)

        UID = str(uuid.uuid4()) + "-"

        # Async Upload: latest checkpoint and previous checkpoint if present
        for local_path, file_name, task_name in [ (OUTPUT_DCD_FILE_LOCAL, OUTPUT_DCD_FILE, 'ul_dcd'), 
                                                  (LOG_FILE_LOCAL,        LOG_FILE,        'ul_log'),
                                                  (CPT_LOCAL,             CPT_FILE,        'ul_cpt'),
                                                  (HISTORY_LOCAL,         HISTORY_FILE,    'ul_history') ]:
            if not os.path.exists(local_path):
                continue 
       
            temp_file = os.path.join(UPLOAD_FOLDER, UID + file_name) # avoid the conflict with the previous one
            shutil.copy(local_path, temp_file) # Make a copy
            message = { 'task': task_name, 
                        'source': temp_file, 'bucket': BUCKET, 'prefix': PREFIX, 'folder': FOLDER, 'target': file_name,
                        'chunk_size_mbtype': "10M", 'concurrency': "10" }
            Notify_Uploader(task_queue, message)  

        old_steps_done = steps_done

        if task_completed == True:
            break

    g_end = time.perf_counter()
    print( "The runtime was {:.3f} seconds".format(g_end - g_start) )  

    Wait_For_Upload_Completion(task_queue)
    Shutdown_SRCG()

if __name__ == "__main__":
    main() # Need exception handling for production use