
from config import JOB_NUMBER, JOB_BATCH_SIZE
from config import Batch_Send
from config import JOB_HISTORY, BUCKET_NAME, REMOTE_FOLDER
import requests
import json
import uuid
import os
import queue


# Override the previous job history and only keep the current jobs
if os.path.exists( os.path.abspath(JOB_HISTORY) ):
    os.remove( os.path.abspath(JOB_HISTORY) )

# Put all jobs into a local job queue first, which is very fast.
# You may use multiple threads to retrieve jobs from this queue, and send them to AWS SQS concurrently
local_job_queue = queue.Queue()

'''
  60 seconds for 1 step;
 600 seconds for saving interval;

 500 steps - 16.7 hours
1000 steps - 16.7 hours
1200 steps - 20.0 hours  # test
2000 steps - 33.3 hours
3000 steps - 50.0 hours
'''
for i in range(JOB_NUMBER):
    #task = { "parameters": { "STATE_SAVING_INTERVAL": "10.0", "STEP_RUNNING_TIME":"1.0" },
    task = { "parameters": { "STATE_SAVING_INTERVAL": "600.0", "STEP_RUNNING_TIME":"60.0" },            
             "bucket": BUCKET_NAME,
             "folder": f"{REMOTE_FOLDER}/job{i}" } 
    local_job_queue.put(task)

local_job_queue.put(None) # Provide an end

# We only use 1 thread to send jobs (send batch) to AWS SQS at this moment
Is_Completed = False
job_no = 0
RID = str(uuid.uuid4()) 
while True:
    
    entries = []
    for count in range(JOB_BATCH_SIZE): 

        job = local_job_queue.get()  # Block here
        local_job_queue.task_done()

        if job is None:
            Is_Completed = True    
            break  
    
        uid = str(job_no) + '-' + 't0-' + RID # only 1 thread at this moment
        whole_job = { "Id": uid, 
                      "MessageBody": json.dumps(job),
                      "MessageAttributes": {},
                      "MessageDeduplicationId": uid, 
                      "MessageGroupId": uid }       
        
        # Save the job into the file for debugging
        with open( os.path.abspath(JOB_HISTORY),'a' ) as f:
            f.write(json.dumps(job))
            f.write('\n')

        print(whole_job)       
        entries.append( whole_job )
        job_no = job_no +1

    if len(entries) > 0:
        Batch_Send(entries)

    if Is_Completed == True: # All jobs have been sent to AWS SQS
        break