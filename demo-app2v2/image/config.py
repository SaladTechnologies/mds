import os
import json
import boto3
from botocore.config import Config
import time
import random 
from enum import Enum
import speedtest
from pythonping import ping
import subprocess
import requests
from dotenv import load_dotenv
load_dotenv()


VISIBILITY_TIMEOUT   = 90   # seconds
RENEWAL_TIME         = 60   # seconds


MAX_UPLOAD_LOG_TIME  = 60   # seconds
MAX_UPLOAD_TIME      = 600  # seconds


g_visibility_timeout_health = True
g_upload_error = 0


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
    print("Retrieving ......", flush=True)
    
    response = sqs_client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=WAIT_TIME) # Block here
    temp = response.get("Messages", []) # return [] if empty    
    if len(temp) > 0:
        for message in temp:
            result.append({ "message": json.loads(message["Body"]),
                            "handle":  message['ReceiptHandle'],
                            "time":    time.perf_counter()         })
        
    return result


# Delete a job from AWS SQS
# It may fail if the job has been deleted by others or the visibility times out
def Delete_A_Job(job):
    try: 
        response = sqs_client.delete_message( QueueUrl=queue_url, ReceiptHandle=job['handle'] )
        print("The job is deleted succssefully from AWS SQS")
    except Exception as e:
        print("Run into trouble, " + str(e))
        return False
    return True


# Extend the visibility timeout of a job in AWS SQS
# It may fail if the job has been deleted by others or the visibility times out
def Renew_A_Job(job, description=""):
    current_time = time.perf_counter() 
    temp = current_time - job['time']
   
    #return False # Make the network the performance bottleneck for testing purposes.
    if temp > VISIBILITY_TIMEOUT:
        print(40 * "R" + " {}: ".format(description), end="")
        print("running {} seconds, already times out", flush=True)
        # Will not update the time in this case
        return False  
    try:
        if temp > RENEWAL_TIME:
            sqs_client.change_message_visibility( QueueUrl=queue_url, ReceiptHandle=job['handle'],
                                                  VisibilityTimeout = VISIBILITY_TIMEOUT )
            job['time'] = current_time
            print(40 * "R" + " {}: ".format(description), end="")
            #print("only {} seconds remaining, ".format(VISIBILITY_TIMEOUT - temp), end="")
            print("the visibility timeout is extended and the time is updated", flush=True)
    except Exception as e:
        print(40 * "R" + " {}: ".format(description) + str(e), flush=True)
        return False
    return True


# Extend the visibility timeout regularly
def VT_Renewal(queue):
    global g_visibility_timeout_health
    job = None    
    while True:
        time.sleep(1)
        if (queue.qsize() > 0): # new job
            job = queue.get()
            queue.task_done()     # task done     
            #print(40 * "R" + " The VTR thread: receive " + json.dumps(job), flush=True)
            print(40 * "R" + " The VTR thread: received the signal", flush=True)
            g_visibility_timeout_health = True

        if job != None:
            g_visibility_timeout_health = Renew_A_Job(job, "The VTR thread") # will update the job["time"]


# Whether the current job is still valid
def Get_Visibility_Timeout_Health():
    return g_visibility_timeout_health


# Upload local files to Cloud Storage and return the result (optional)
def Uploader(queue, ack_queue):
    global g_upload_error 
    while True:
        task = queue.get()  # Block here
        #time.sleep( random.randint(1, 20) ) # Make the network the performance bottleneck for testing purposes.
        #time.sleep( 60 ) # Make the network the performance bottleneck for testing purposes.

        result = True
        for sub_task in task['sub_tasks']:  
            try: 
                # first upload the data files, and finally upload the metadata file (step/progress)
                # A metadata file serves as index for one or more data files.
                print(40 * "U" + " The UL thread: upload " + sub_task['target'], flush=True)
                s3.upload_file(sub_task['source'], sub_task['bucket'], sub_task['target'] )  
            except Exception as e:
                print(40 * "U" + " The UL thread: " +str(e), flush=True)
                result = False
                g_upload_error = g_upload_error + 1 # Error !!!!!!
            os.remove( sub_task['source'] )

        if task["requiring_ack"] == True: # The main thread will check the result 
            ack_queue.put(result)         # True when all files have been uploaded successfully

        queue.task_done()     # task done        


# Are there some errors during the previous upload tasks
def Get_Upload_Error():
    return g_upload_error 

def Reset_Upload_Error():
    global g_upload_error 
    g_upload_health = 0


# Wait until the previous upload task completes and return the result
class WAITING(Enum):
    SUCCESS = 0 # True when all files have been uploaded successfully
    FAILURE = 1 # Many reasons: All or parts of uploads failed (no access, conn timeout, upload timeout)
    TIMEOUT = 2
def Wait( ack_queue, max_time ):
    for _ in range(max_time):
        time.sleep(1)
        if(ack_queue.qsize() > 0):
            temp = ack_queue.get() 
            ack_queue.task_done()         # task done
            if temp:
                return WAITING.SUCCESS    
            else:
                return WAITING.FAILURE    
    return WAITING.TIMEOUT  # Addtional timeout setting (different from the s3.upload timeout)


# Trigger the node reallocation
# Trigger reallocation here if a node is not suitable: http://169.254.169.254/v1/reallocate
# https://docs.salad.com/products/sce/container-groups/imds/imds-reallocate
def Reallocate(local, reason):
    print(reason)
    if (local):  # Run locally
        print("Call the exit(1) ......")
        os._exit(1)
    else:        # Run on SaladCloud
        print("Call the IMDS reallocate ......")
        url = "http://169.254.169.254/v1/reallocate"
        headers = {'Content-Type': 'application/json',
                   'Metadata': 'true'}
        body = {"Reason": reason}
        response = requests.post(url, headers=headers, json=body)
        print(response) # The instance will become inactive after a few seconds
        print("See you later")
        time.sleep(10)


# Test network bandwdith
def network_test():
    print("Test the network speed ....................", flush=True)
    try:
        speed_test = speedtest.Speedtest()
        bserver = speed_test.get_best_server()
        dlspeed = int(speed_test.download() / (1000 * 1000))  # Convert to Mbps, not Mib
        ulspeed = int(speed_test.upload() / (1000 * 1000))  # Convert to Mbps, not Mib
        latency = bserver['latency'] # the latency to the test server
        country = bserver['country'] 
        location = bserver['name']
    except Exception as e:  
        return "", "", 99999, 0, 0
    return country, location, latency, dlspeed, ulspeed    


# Test network latency
# Only the root user can run this code - no issue in containers
def ping_test(tCount=10):
    print("Test the latency ....................", flush=True)
    try:
        print("To: ec2.us-east-1.amazonaws.com")
        temp = ping('ec2.us-east-1.amazonaws.com', interval=1, count=tCount, verbose=True)
        latency_useast1 = temp.rtt_avg_ms      
        print("To: ec2.eu-central-1.amazonaws.com")  
        temp = ping('ec2.eu-central-1.amazonaws.com', interval=1, count=tCount,verbose=True)
        latency_eucentral1 = temp.rtt_avg_ms
    except Exception as e:  
        return 99999,99999
    return latency_useast1, latency_eucentral1


# Read the CUDA Version
def Get_CUDA_Version():
    try:
        cmd = 'nvidia-smi'
        output = subprocess.check_output(cmd, shell=True, text=True)
        output = output.split("\n")[2]
        output = output.split("CUDA Version: ")[-1]
        version = float(output.split(" ")[0])
    except Exception as e: 
        return 0
    return version 


# Get the GPU info
def Get_GPU():
    try:
        result = {}
        cmd = 'nvidia-smi --query-gpu=gpu_name,memory.total,memory.used,memory.free,utilization.memory,temperature.gpu,utilization.gpu --format=csv,noheader'
        output = subprocess.check_output(cmd, shell=True, text=True)
        result['gpu'], result['vram_total'], result['vram_used'], result['vram_free'], result['vram_utilization'], result['gpu_temperature'], result['gpu_utilization'] = output.strip().split(', ')
    except Exception as e:
        return {}
    return result 
    