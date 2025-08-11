from salad_cloud_sdk import SaladCloudSdk
from salad_cloud_sdk.models import ContainerGroupCreationRequest
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
load_dotenv()

# SaladCloud parameters
SALAD_API_KEY        = os.getenv("SALAD_API_KEY")
SALAD_ORGANIZATION    = os.getenv("SALAD_ORGANIZATION")
SALAD_PROJECT         = os.getenv("SALAD_PROJECT")

CONTAINER_GROUP_NAME = os.getenv("CONTAINER_GROUP_NAME") 

sdk = SaladCloudSdk(
    api_key=SALAD_API_KEY, 
    timeout=10000
)

result = sdk.container_groups.get_container_group(
    organization_name=SALAD_ORGANIZATION,
    project_name=SALAD_PROJECT,
    container_group_name=CONTAINER_GROUP_NAME
)
print(result)
print(result.id_) # This is the SALAD_CONTAINER_GROUP_ID