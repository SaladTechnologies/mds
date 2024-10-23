from config import JOB_HISTORY
from config import Delete_A_Job, Retrieve_Jobs
import os

print(60 * "-" + " Delete jobs from AWS SQS")
while True:
    batch_jobs = Retrieve_Jobs(1)
    if(len(batch_jobs) == 0):
        break
    
    for job in batch_jobs:
        print(job[0])
        Delete_A_Job(job[1]) 


# Delete the job history
if os.path.exists( os.path.abspath(JOB_HISTORY) ):
    os.remove( os.path.abspath(JOB_HISTORY) )
    print("{} is deleted.".format(os.path.abspath(JOB_HISTORY)))


