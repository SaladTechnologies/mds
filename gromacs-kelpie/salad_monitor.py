
import os
import time
import boto3
import sys
import json
from boto3.s3.transfer import TransferConfig
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

AWS_ACCESS_KEY_ID      = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY  = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_ENDPOINT_URL       = os.getenv("AWS_ENDPOINT_URL")
AWS_REGION             = os.getenv("AWS_REGION")

BUCKET     = os.getenv("BUCKET")
PREFIX     = os.getenv("PREFIX")
FOLDER     = ""

S3Client = boto3.client(
    "s3",
    endpoint_url=AWS_ENDPOINT_URL,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION 
)

g_files = []

# Function to list files in the global g_files list
def listFiles():
    for i in range(len(g_files)):   
        print(f"{i}: {g_files[i]}")

# Function to fetch files from the bucket and store them in the g_files 
def fetchFiles():
    global g_files

    g_files = []  # Reset the global list to avoid duplicates
    
    if not BUCKET or not PREFIX or not FOLDER:
        print("Missing BUCKET, PREFIX, or FOLDER")
        return []

    paginator = S3Client.get_paginator('list_objects_v2')
    files = []
    for page in paginator.paginate(
        Bucket=BUCKET,
        Prefix=PREFIX + "/" + FOLDER
    ):
        for obj in page.get('Contents', []):
            # Remove the folder prefix from the key if you want just the file name
            key = obj['Key']
            if key.endswith('/'):
                continue  # skip folder itself
            files.append(key)
            g_files.append(key.split('/')[-1])  # store just the file name    

def showFile(file_name):
    if not BUCKET or not PREFIX or not FOLDER:
        print("Missing BUCKET, PREFIX, or FOLDER")
        return
    
    if PREFIX != "":
        key = f"{PREFIX}/{FOLDER}/{file_name}"
    else:
        key = f"{FOLDER}/{file_name}"

    try:
        response =  S3Client.get_object(Bucket=BUCKET, Key=key)
        content = response['Body'].read().decode('utf-8')
        
        print(f"\nContent of {file_name}: \n{content}")

        # Save to local file
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Saved to local file: {file_name}")

    except Exception as e:
        print(f"Failed to get {key}: {e}")

def resetFolder():

    if not BUCKET or not PREFIX or not FOLDER:
        print("Missing BUCKET, PREFIX, or FOLDER")
        return []

    paginator = S3Client.get_paginator('list_objects_v2')
    to_delete = []
    for page in paginator.paginate(
        Bucket=BUCKET,
        Prefix=PREFIX + "/" + FOLDER
    ):
        for obj in page.get('Contents', []):
            key = obj['Key']
            if key.endswith('/'):
                continue  # skip folder itself
            if (key.split('/')[-1].split('.')[-1] != 'tpr'):  # remove the folder prefix
                to_delete.append({'Key': key})
            else:
                print(f"Skipping deletion of TPR file: {BUCKET}/{key}")

    if to_delete:
        # S3 allows deleting up to 1000 objects per request
        for i in range(0, len(to_delete), 1000):
            S3Client.delete_objects(
                Bucket=BUCKET,
                Delete={'Objects': to_delete[i:i+1000]}
            )
        print(f"Deleted {len(to_delete)} objects from {BUCKET}/{PREFIX}{FOLDER}/")
    else:
        print("No objects to delete.")
    
def run():
    global FOLDER

    while True:
        if not FOLDER:
            print("\nSet the job folder first.")
        else:
            print("\nThe job folder:", FOLDER)
        
        cmd = input("Enter (job_folder, file ID, l-list files,f-fetch new files, reset-purge, e-exit): ").strip()

        if not cmd:
            continue
        if cmd == "f":
            fetchFiles()
            listFiles()
        elif cmd == "l":
            listFiles()
        elif cmd == "reset":
            resetFolder()
        elif cmd == "e":
            print("Exiting.")
            exit(0)
        elif cmd.isdigit():
            if int(cmd) < len(g_files):
                showFile( g_files[int(cmd)])
        else:
            FOLDER = cmd


if __name__ == "__main__":
    run()