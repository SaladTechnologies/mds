from salad_cloud_sdk import SaladCloudSdk
from salad_cloud_sdk.models import ContainerGroupCreationRequest
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
load_dotenv()

# Access to the Cloudflare R2 bucket 
CLOUDFLARE_ID             = os.getenv("CLOUDFLARE_ID", "")
CLOUDFLARE_KEY            = os.getenv("CLOUDFLARE_KEY", "")
CLOUDFLARE_ENDPOINT_URL   = os.getenv("CLOUDFLARE_ENDPOINT_URL", "")

# Task parameters
BUCKET                = os.getenv("BUCKET")
PREFIX                = os.getenv("PREFIX","")  # Optional, can be empty
FOLDER                = os.getenv("FOLDER")
TPR_FILE              = os.getenv("TPR_FILE")  
MAX_STEPS             = int(os.getenv("MAX_STEPS"))  
SAVING_INTERVAL_HOURS = os.getenv("SAVING_INTERVAL_HOURS") 
MAX_NO_RESPONSE_TIME = int(os.getenv("MAX_NO_RESPONSE_TIME","3600")) # Second

# SaladCloud parameters
SALAD_API_KEY        = os.getenv("SALAD_API_KEY","")
ORGANIZATION_NAME    = os.getenv("ORGANIZATION_NAME","")
PROJECT_NAME         = os.getenv("PROJECT_NAME","")
CONTAINER_GROUP_NAME = os.getenv("CONTAINER_GROUP_NAME","") 

# Dynamic creation
TASK_CREATION_TIME    = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S")  

IMAGE                 = os.getenv("IMAGE", "")

########################################
########################################

sdk = SaladCloudSdk(
    api_key=SALAD_API_KEY, 
    timeout=10000
)

request_body = ContainerGroupCreationRequest(
   name=CONTAINER_GROUP_NAME,        
   display_name=CONTAINER_GROUP_NAME,
   container={
       "image": IMAGE,

       # 16 vCPU, 24 GB memory, RTX 4090(24G B), 50 GB Disk Space 
       "resources": {
           "cpu": 16,
           "memory": 24576,
           "gpu_classes": ['ed563892-aacd-40f5-80b7-90c9be6c759b', # 4090 - 20GB
                           '0d062939-7c01-4aae-a2b1-30e315124e51', # 4080 - 16GB
                           'f1380143-51cd-4bad-80cb-1f86ee6b49fe', # 4070 Ti Super - 16GB
                           'de00c90b-904b-4d9e-8fc9-1d9a08eb0932', # 4070 Ti - 12 GB
                           '2b73eef8-be49-4667-8fc0-5c0cb127cfe0', # 4060 Ti - 16GB
                           ],
           "storage_amount": 53687091200,
       },  # 50 GB
    
       #"command": ['sh', '-c', 'sleep infinity' ],
       
       "priority": "high",
       "environment_variables": {
               "CLOUDFLARE_ENDPOINT_URL": CLOUDFLARE_ENDPOINT_URL,
               "CLOUDFLARE_ID": CLOUDFLARE_ID,
               "CLOUDFLARE_KEY": CLOUDFLARE_KEY,

               "BUCKET": BUCKET,             
               "PREFIX": PREFIX,              
               "FOLDER": FOLDER,                 
               "TPR_FILE": TPR_FILE,             
               "MAX_STEPS": MAX_STEPS,           
               "SAVING_INTERVAL_HOURS": SAVING_INTERVAL_HOURS,
               "MAX_NO_RESPONSE_TIME": MAX_NO_RESPONSE_TIME,

               "TASK_CREATION_TIME": TASK_CREATION_TIME,

               "SALAD_API_KEY": SALAD_API_KEY,
               "ORGANIZATION_NAME": ORGANIZATION_NAME,
               "PROJECT_NAME": PROJECT_NAME,
               "CONTAINER_GROUP_NAME": CONTAINER_GROUP_NAME,               
        }
   },
   autostart_policy=True,
   restart_policy="always",
   replicas=1,
   country_codes=[ "us" ]
)

print(request_body)


result = sdk.container_groups.create_container_group(
   request_body=request_body,
   organization_name=ORGANIZATION_NAME,
   project_name=PROJECT_NAME
)
print(result)

result = sdk.container_groups.get_container_group(
    organization_name=ORGANIZATION_NAME,
    project_name=PROJECT_NAME,
    container_group_name=CONTAINER_GROUP_NAME 
)
print(result)