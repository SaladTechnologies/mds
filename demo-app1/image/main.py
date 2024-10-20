import os
import signal
import time

salad_machine_id = os.getenv("SALAD_MACHINE_ID", "NULL")

# The job input: begin and end
# To calculate the sum of the series from start to end, which includes start, start + 1, start + 2, and so on.

# The job state:
# (1) running data, t and sum_t, meaning the sum from start to t.
# (2) logs,  all machines that have participated in executing this job.

# The job output: sum and logs

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

# Read the job input: start and end
try:
    with open(input_file, 'r') as f:
        g_Start, g_End = f.read().splitlines()
        g_Start, g_End = int(g_Start), int(g_End)
except FileNotFoundError:
    with open(output_file, 'w') as f: # Save the job output
        f.write('ERROR - no input')
        print('ERROR - no input', flush=True)
        exit(0) # The job has finished although it failed

# Handle the exception
if g_Start > g_End:
    with open(output_file, 'w') as f: # Save the job output
      f.write('ERROR - wrong input')
      print('ERROR - wrong input', flush=True)
      exit(0) # The job has finished although it failed

print(f'The job is to calculate the sum of {g_Start} ... {g_End}', flush=True)

# Read the job state - logs
g_logs = []
try:
    with open(logs_file, 'r') as f:
        for temp in f.read().splitlines():
            g_logs.append(temp)
except FileNotFoundError:
    pass

# Read the job state - running data: t and sum_t
g_finishedStep = g_Start - 1
g_tempSum = 0
try:
    with open(state_file, 'r') as f:
        g_finishedStep, g_tempSum = f.read().splitlines()
        g_finishedStep, g_tempSum = int(g_finishedStep), int(g_tempSum)
        print(f'Unfinished job, resume from the previous state: the sum of {g_Start} ... {g_finishedStep} is {g_tempSum}', flush=True)
except FileNotFoundError:
    print('New job, start from scratch', flush=True)

# Run the job - long running and interruptible
time_start = time.perf_counter()
for x in range(g_finishedStep+1, g_End+1):

    g_tempSum = g_tempSum + x
    time.sleep(step_running_time)
    time_end = time.perf_counter()

    if (time_end - time_start) > state_saving_internal:
        time_start = time.perf_counter()

        g_logs.append(f'{salad_machine_id} {x}') # Record this event

        with open(logs_file, 'w') as f:  # Save the job state - logs
            for item in g_logs[0:-1]:
                f.write(f"{item}\n")
            f.write(g_logs[-1])

        with open(state_file, 'w') as f:  # Save the job state - running: t and sum_t
                                          # The Kelpie worker will upload this folder if any changes occur while the code is running
            temp = str(x) + '\n' + str(g_tempSum)
            f.write(temp)
            print(f'Save the status every {state_saving_internal} seconds: the sum of {g_Start} ... {x} is {g_tempSum}', flush=True)

# Record this event, there might be some addtional steps after the last save state
g_logs.append(f'{salad_machine_id} {x}') 

# Save the job output with logs
with open(output_file, 'w') as f:
    f.write(f"{g_tempSum}")
    for item in g_logs:
        f.write(f"\n{item}")

print(f'The job output: the sum of {g_Start} ... {g_End} is {g_tempSum}', flush=True)
exit(0)

# If code exits normally, the Kelpie worker will upload this folder and report the job status as completed.
 