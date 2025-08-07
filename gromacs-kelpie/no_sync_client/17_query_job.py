import requests
import json
import os
from dotenv import load_dotenv
load_dotenv()

JOB_HISTORY    = os.getenv("JOB_HISTORY")

KELPIE_API_URL = os.getenv("KELPIE_API_URL") 
KELPIE_API_KEY = os.getenv("KELPIE_API_KEY")

if not os.path.exists( os.path.abspath(JOB_HISTORY) ):
    print("{} is not existed.".format(os.path.abspath(JOB_HISTORY)))
    exit(0)

Job_IDs= []
with open( os.path.abspath(JOB_HISTORY),'r' ) as f:
    Job_IDs = f.read().splitlines()

for jid in Job_IDs:
    headers = { "Content-Type": "application/json", "X-Kelpie-Key": KELPIE_API_KEY }
    response = requests.get(KELPIE_API_URL + "/jobs/" + jid, headers=headers) 
    temp = response.json()
    print( json.dumps(temp, indent=4) )
  
        