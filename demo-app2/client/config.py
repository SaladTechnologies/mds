import os
import json
import boto3
from dotenv import load_dotenv
load_dotenv()

# Keep the previous jobs sent to AWS SQS
JOB_HISTORY = "job_history.txt"

JOB_BATCH_SIZE = 2  # The number of jobs sent to AWS SQS at a time
JOB_NUMBER = 5     # How many jobs are submitted during a test

LOCAL_JOB_DIR = "local_jobs"  # The local folder to keep all job data
REMOTE_FOLDER = "demoapp2"    # A folder in a cloud storage bucket
                              # It contains all job data ( the input, state, logs and output of each job)
BUCKET_NAME   = "transcripts" # We use a cloud storage bucket named "transcriptions" in Cloudflare R2

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


# Send a batch of jobs to AWS SQS
def Batch_Send(entries, description=""):
    response = sqs_client.send_message_batch(QueueUrl=queue_url, Entries=entries)
    ''' 
    if "Successful" in response:
        print("{} has successfully sent:".format(description))
        for msg_meta in response["Successful"]:
            for x in entries:
                if x['Id'] == msg_meta['Id']:
                    print(x['MessageBody'])
    
    if "Failed" in response:
        print("{} failed to send:".format(description))
        for msg_meta in response["Failed"]:
            for x in entries:
                if x['Id'] == msg_meta['Id']:
                    print(x['MessageBody'])
    '''


# Query the Job Queue - AWS SQS
def Query_Queue():
    result = sqs_client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=['All'])
    x = result['Attributes']['ApproximateNumberOfMessages']
    y = result['Attributes']['ApproximateNumberOfMessagesNotVisible']
    sum = int(x) + int(y)

    print("{} in the queue".format(sum),end=": ")
    print("{} available and".format(x), end=" ")
    print("{} being processed".format(y))


# Delete a job from AWS SQS
def Delete_A_Job(receipt_handle, description=""):
    try: 
        response = sqs_client.delete_message( QueueUrl=queue_url, ReceiptHandle=receipt_handle )
        #print(response['ResponseMetadata']['HTTPStatusCode'])
    except Exception as e:
        print("{} run into trouble:".format(description))
        print(str(e))

# Retrieve up to 10 jobs from AWS SQS, and then return 
def Retrieve_Jobs( WAIT_TIME, description="" ):    
    result = []
    try:
        response = sqs_client.receive_message(
                    QueueUrl=queue_url, MaxNumberOfMessages=10, WaitTimeSeconds=WAIT_TIME)
        temp = response.get("Messages", []) # get [] if empty
        for message in temp:
            temp1 = json.loads( message["Body"] )
            temp2 = message['ReceiptHandle']
            result.append( [ temp1,temp2 ] )
    except Exception as e:
        print("{} run into trouble:".format(description))
        print(str(e))
        
    return result