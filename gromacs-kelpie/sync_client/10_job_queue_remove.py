import requests
import json
import os
from dotenv import load_dotenv
load_dotenv()

JOB_HISTORY    = os.getenv("JOB_HISTORY")

KELPIE_API_URL = os.getenv("KELPIE_API_URL") 
SALAD_API_KEY      = os.getenv("SALAD_API_KEY")
SALAD_ORGANIZATION = os.getenv("SALAD_ORGANIZATION")
SALAD_PROJECT      = os.getenv("SALAD_PROJECT")

if not os.path.exists( os.path.abspath(JOB_HISTORY) ):
    print("{} is not existed.".format(os.path.abspath(JOB_HISTORY)))
    exit(0)

Job_IDs= []
with open( os.path.abspath(JOB_HISTORY),'r' ) as f:
    Job_IDs = f.read().splitlines()

kelpie_headers = {
    "Salad-Api-Key": SALAD_API_KEY,
    "Salad-Organization": SALAD_ORGANIZATION,
    "Salad-Project": SALAD_PROJECT,
    "Content-Type": "application/json"
}

for jid in Job_IDs:
    response = requests.delete(KELPIE_API_URL + "/jobs/" + jid, headers=kelpie_headers) # delete
    temp = response.json()
    print( json.dumps(temp, indent=4) )
    # print(temp['id'], temp["status"])
        
os.remove( os.path.abspath(JOB_HISTORY) )
print("{} is deleted.".format(os.path.abspath(JOB_HISTORY)))