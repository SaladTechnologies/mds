from config import TASK_NUMBER, BUCKET_NAME, REMOTE_FOLDER
from config import JOB_HISTORY, CONTAINER_GROUP_ID
from config import KELPIE_API_KEY, KELPIE_API_URL
import requests
import json
import os

if os.path.exists( os.path.abspath(JOB_HISTORY) ):
    print("{} is existed.".format(os.path.abspath(JOB_HISTORY)))
    exit(0)


for i in range(TASK_NUMBER):
    task = {
    "command": "python",
    "arguments": [
     "/app/main.py"
    ] ,
    "environment": { "STATE_SAVING_INTERVAL": "600.0", "STEP_RUNNING_TIME":"60.0" },
    #"environment": { "STATE_SAVING_INTERVAL": "9.0", "STEP_RUNNING_TIME":"1.0" },
    "container_group_id": CONTAINER_GROUP_ID,
    "sync": {
      "before": [
        {
          "bucket": BUCKET_NAME,
          "prefix": f"{REMOTE_FOLDER}/job{i}/input",
          "local_path": "/app/data/input/",
          "direction": "download",  # downloading input
        },
        {
          "bucket": BUCKET_NAME,
          "prefix": f"{REMOTE_FOLDER}/job{i}/state",
          "local_path": "/app/data/state/",
          "direction": "download"   # downloading state - running data and logs
        }
      ],
      "during": [
        {
          "bucket": BUCKET_NAME,
          "prefix": f"{REMOTE_FOLDER}/job{i}/state",
          "local_path": "/app/data/state/",
          "direction": "upload"     # uploading state - running data and logs
        }
      ],
      "after": [
        {
          "bucket": BUCKET_NAME,
          "prefix": f"{REMOTE_FOLDER}/job{i}/output",
          "local_path": "/app/data/output/",
          "direction": "upload"     # uploading output and log
        }
      ]}
    }

    headers = { "Content-Type": "application/json", "X-Kelpie-Key": KELPIE_API_KEY }
    response = requests.post(KELPIE_API_URL+ "/jobs", headers=headers, json=task) # pst
    temp = response.json()
    print(json.dumps(temp, indent=4))

    ID = temp["id"]

    with open( os.path.abspath(JOB_HISTORY),'a' ) as f:
        f.write(ID)
        f.write('\n')