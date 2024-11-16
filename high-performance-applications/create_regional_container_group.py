from salad_cloud_sdk import SaladCloudSdk
from salad_cloud_sdk.models import CreateContainerGroup
import os
from dotenv import load_dotenv
load_dotenv()

SALAD_API_KEY = os.getenv("SALAD_API_KEY","")
ORGANIZATION_NAME = os.getenv("ORGANIZATION_NAME","")
PROJECT_NAME = os.getenv("PROJECT_NAME","")

GROUP_NAME = "regional-group-001"

sdk = SaladCloudSdk(
    api_key=SALAD_API_KEY, 
    timeout=10000
)

request_body = CreateContainerGroup(
   name=GROUP_NAME,        
   display_name=GROUP_NAME,
   container={
       "image": "saladtechnologies/misc:0.0.3-flask3",
       "resources": {
           "cpu":4,
           "memory": 4096,
            "gpu_classes":['f1380143-51cd-4bad-80cb-1f86ee6b49fe', '0d062939-7c01-4aae-a2b1-30e315124e51', '2b73eef8-be49-4667-8fc0-5c0cb127cfe0'],
       },
       "priority": "high",
       "environment_variables": {},
   },
   autostart_policy=False,
   restart_policy="always",
   replicas=3,
   country_codes=[ "us","ca","mx" ], 
   networking={
       "protocol": "http",
       "port": 8000,
       "auth": False,
       "load_balancer": "least_number_of_connections",
       "single_connection_limit": False,
       "client_request_timeout": 100000,
       "server_response_timeout": 100000
   }
)

result = sdk.container_groups.create_container_group(
   request_body=request_body,
   organization_name=ORGANIZATION_NAME,
   project_name=PROJECT_NAME
)
print(result)

result = sdk.container_groups.get_container_group(
    organization_name=ORGANIZATION_NAME,
    project_name=PROJECT_NAME,
    container_group_name=GROUP_NAME 
)
print(result)
