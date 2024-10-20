from config import TASK_NUMBER
from config import JOB_HISTORY
from config import KELPIE_API_KEY, KELPIE_API_URL
import requests
import json
import os

if not os.path.exists( os.path.abspath(JOB_HISTORY) ):
    print("{} is not existed.".format(os.path.abspath(JOB_HISTORY)))
    exit(0)

Job_IDs= []
with open( os.path.abspath(JOB_HISTORY),'r' ) as f:
    Job_IDs = f.read().splitlines()

for i in range(TASK_NUMBER):
    headers = { "Content-Type": "application/json", "X-Kelpie-Key": KELPIE_API_KEY }
    response = requests.get(KELPIE_API_URL + "/jobs/" + Job_IDs[i], headers=headers) # get
    temp = response.json()
    print( json.dumps(temp, indent=4) )
    #print(temp['id'], temp["status"])     
        