import os
import boto3
from dotenv import load_dotenv
load_dotenv()


'''
The CONTAINER_GROUP_ID ensures that jobs submitted to the Kelpie platform are processed 
only by instances within a specific container group. It must match the actual SALAD_CONTAINER_GROUP_ID 
when running the image on SaladCloud. You can retrieve this ID (using env command) by logging into any 
running instance on SaladCloud.

If you run the image locally, the CONTAINER_GROUP_ID in the config.py file needs to 
match the environment variable - SALAD_CONTAINER_GROUP_ID used while running the image.
'''

#CONTAINER_GROUP_ID = "LOCAL_TEST"   
CONTAINER_GROUP_ID = "8e78dce7-08b8-4854-b6ea-67a6bb6bcf03"


# Keep the job IDs of all submitted jobs, which are used to query their status - PENDING, COMPLETED, RUNNING, FAILED..
JOB_HISTORY = "job_history.txt"

TASK_NUMBER = 1 # How many jobs are submitted for a test

LOCAL_JOB_DIR = "local_jobs"  # The local folder to keep all job data
REMOTE_FOLDER = "demoapp1"    # A folder in a cloud storage bucket
                              # It contains all job data ( the input, state and output of each job)
BUCKET_NAME   = "transcripts" # We use a cloud storage bucket named "transcriptions" in Cloudflare R2

KELPIE_API_URL = os.getenv("KELPIE_API_URL") 
KELPIE_API_KEY = os.getenv("KELPIE_API_KEY")

CLOUD_STORAGE_URL        = os.getenv("CLOUD_STORAGE_URL")
CLOUD_STORAGE_REGION     = os.getenv("CLOUD_STORAGE_REGION")
CLOUD_STORAGE_KEY_ID     = os.getenv("CLOUD_STORAGE_KEY_ID")
CLOUD_STORAGE_ACCESS_KEY = os.getenv("CLOUD_STORAGE_ACCESS_KEY")

s3 = boto3.client(
    service_name ="s3",
    endpoint_url = CLOUD_STORAGE_URL,
    aws_access_key_id = CLOUD_STORAGE_KEY_ID,
    aws_secret_access_key = CLOUD_STORAGE_ACCESS_KEY,
    region_name = CLOUD_STORAGE_REGION
)
