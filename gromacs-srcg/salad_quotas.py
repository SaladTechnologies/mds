from salad_cloud_sdk import SaladCloudSdk
import os
from dotenv import load_dotenv
load_dotenv()

SALAD_API_KEY = os.getenv("SALAD_API_KEY","")
ORGANIZATION_NAME = os.getenv("ORGANIZATION_NAME","")
PROJECT_NAME = os.getenv("PROJECT_NAME","")
CONTAINER_GROUP_NAME = os.getenv("CONTAINER_GROUP_NAME","")

sdk = SaladCloudSdk(
    api_key=SALAD_API_KEY, 
    timeout=10000
)

result = sdk.quotas.get_quotas(organization_name=ORGANIZATION_NAME)
print(result)

result = sdk.organization_data.list_gpu_classes(organization_name=ORGANIZATION_NAME)

for x in result.items:
   if '40' in x.name:
       print(f'ID {x.id_}, Name {x.name}, high {x.prices[0].price}, medium {x.prices[1].price}, low {x.prices[2].price}, batch {x.prices[3].price}')
