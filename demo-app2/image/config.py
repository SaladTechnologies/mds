import os
import json
import boto3
import time
import random 
from dotenv import load_dotenv
load_dotenv()


# Access to the Job Queue System - AWS SQS
queue_url  = os.getenv("QUEUE_URL","")
aws_id     = os.getenv("AWS_ID", "")
aws_key    = os.getenv("AWS_KEY", "")
sqs_client = boto3.client( service_name ="sqs",
                           aws_access_key_id = aws_id, aws_secret_access_key = aws_key,                
                           region_name="us-east-2")


#  Access to the Cloud Storage - Cloudflare R2 (AWS S3-Compatible)
cloudflare_url    = os.getenv("CLOUDFLARE_URL", "")
cloudflare_region = os.getenv("CLOUDFLARE_REGION", "")
cloudflare_id     = os.getenv("CLOUDFLARE_ID", "")
cloudflare_key    = os.getenv("CLOUDFLARE_KEY", "")
s3 = boto3.client( service_name ="s3", endpoint_url = cloudflare_url,
                   aws_access_key_id = cloudflare_id, aws_secret_access_key = cloudflare_key,
                   region_name = cloudflare_region )


# We don't need to catch any exceptions here. 
# If something goes wrong, it will exit, triggering reallocation.
def Retrieve_A_Job(WAIT_TIME=10):    
    result = []
    response = sqs_client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=WAIT_TIME) # Block here
    temp = response.get("Messages", []) # return [] if empty
    
    if len(temp) > 0:
        for message in temp:
            temp1 = json.loads(message["Body"])  # Job
            temp2 = message['ReceiptHandle']     # The handle to delete the job later
            result.append([ temp1,temp2 ])
        
    return result


# Delete a job from AWS SQS
# It may fail if the job has been deleted by others or the visibility times out
def Delete_A_Job(receipt_handle, description=""):
    try: 
        response = sqs_client.delete_message( QueueUrl=queue_url, ReceiptHandle=receipt_handle )
    except Exception as e:
        print("{}: run into trouble:".format(description))
        print(str(e))


# Upload local files to Cloud Storage, and delete the job from AWS SQS (after the final output is uploaded)
# Trigger reallocation if errors
def Uploader(queue):
    
    while True:
        task = queue.get()  # Block here
 
         # time.sleep( random.randint(1, 20) ) # Make the network the bottleneck of performance for tests

        for stask in task['sub_tasks']:  
            # Could be interrupted here -> may consolidate multiple uploads into a single upload

            print(40 * "-" + " The UL thread: upload " + stask['target'], flush=True)
            s3.upload_file(stask['source'], stask['bucket'], stask['target'] )  

            #print(40 * "-" + " The UL thread: remove " + stask['source'], flush=True)
            os.remove( stask['source'] )
        
        if task["msg_handler"] != None: 
            Delete_A_Job(task["msg_handler"], 'The UL thread')
            print(40 * "-" + " The UL thread: the job is deleted from AWS SQS !!!!!!", flush=True)

        queue.task_done()        

