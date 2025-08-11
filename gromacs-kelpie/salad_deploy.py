from salad_cloud_sdk import SaladCloudSdk
from salad_cloud_sdk.models import ContainerGroupCreationRequest
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
load_dotenv()

# Access to the Cloudflare R2 bucket 
AWS_ACCESS_KEY_ID      = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY  = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_ENDPOINT_URL       = os.getenv("AWS_ENDPOINT_URL")
AWS_REGION             = os.getenv("AWS_REGION")

# SaladCloud parameters
SALAD_API_KEY          = os.getenv("SALAD_API_KEY")
SALAD_ORGANIZATION     = os.getenv("SALAD_ORGANIZATION")
SALAD_PROJECT          = os.getenv("SALAD_PROJECT")

CONTAINER_GROUP_NAME   = os.getenv("CONTAINER_GROUP_NAME") 
IMAGE                  = os.getenv("IMAGE")

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
               "AWS_ACCESS_KEY_ID": AWS_ACCESS_KEY_ID,
               "AWS_SECRET_ACCESS_KEY": AWS_SECRET_ACCESS_KEY,
               "AWS_ENDPOINT_URL": AWS_ENDPOINT_URL,
               "AWS_REGION": AWS_REGION,
               "SALAD_PROJECT": SALAD_PROJECT,
        }
   },
   autostart_policy=True,
   restart_policy="always",
   replicas=1,
   # country_codes=[ "us" ]
)

#print(request_body)


result = sdk.container_groups.create_container_group(
   request_body=request_body,
   organization_name=SALAD_ORGANIZATION,
   project_name=SALAD_PROJECT
)
print(result)
print(result.id_) # This is the SALAD_CONTAINER_GROUP_ID

result = sdk.container_groups.get_container_group(
    organization_name=SALAD_ORGANIZATION,
    project_name=SALAD_PROJECT,
    container_group_name=CONTAINER_GROUP_NAME 
)
print(result)
print(result.id_) # This is the SALAD_CONTAINER_GROUP_ID