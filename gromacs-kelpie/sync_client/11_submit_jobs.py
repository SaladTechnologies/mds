import requests
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
load_dotenv()

SALAD_CONTAINER_GROUP_ID = os.getenv("SALAD_CONTAINER_GROUP_ID")

BUCKET             = os.getenv("BUCKET")
PREFIX             = os.getenv("PREFIX")

JOB_HISTORY        = os.getenv("JOB_HISTORY")

KELPIE_API_URL     = os.getenv("KELPIE_API_URL") 
SALAD_API_KEY      = os.getenv("SALAD_API_KEY")
SALAD_ORGANIZATION = os.getenv("SALAD_ORGANIZATION")
SALAD_PROJECT      = os.getenv("SALAD_PROJECT")

KELPIE_MANAGED_UPLOAD_FOLDER = "/app/kelpie_managed_upload_folder/"

if os.path.exists( os.path.abspath(JOB_HISTORY) ):
    print("{} is existed.".format(os.path.abspath(JOB_HISTORY)))
    exit(0)

jobs = [
    #{ "BUCKET":BUCKET, "PREFIX":PREFIX, "FOLDER":"job1", "TPR_FILE":"j1.tpr", "MAX_STEPS":"50000", "SAVING_INTERVAL_HOURS":"0.167" },
    { "BUCKET":BUCKET, "PREFIX":PREFIX, "FOLDER":"job2", "TPR_FILE":"j2.tpr", "MAX_STEPS":"50000", "SAVING_INTERVAL_HOURS":"0.0167" },
    #{ "BUCKET":BUCKET, "PREFIX":PREFIX, "FOLDER":"job3", "TPR_FILE":"j3.tpr", "MAX_STEPS":"50000", "SAVING_INTERVAL_HOURS":"0.167" },
    #{ "BUCKET":BUCKET, "PREFIX":PREFIX, "FOLDER":"job4", "TPR_FILE":"j4.tpr", "MAX_STEPS":"50000", "SAVING_INTERVAL_HOURS":"0.167" },
    #{ "BUCKET":BUCKET, "PREFIX":PREFIX, "FOLDER":"job5", "TPR_FILE":"j5.tpr", "MAX_STEPS":"50000", "SAVING_INTERVAL_HOURS":"0.167" },
    #{ "BUCKET":BUCKET, "PREFIX":PREFIX, "FOLDER":"job6", "TPR_FILE":"j6.tpr", "MAX_STEPS":"50000", "SAVING_INTERVAL_HOURS":"0.167" },
]

kelpie_headers = {
    "Salad-Api-Key": SALAD_API_KEY,
    "Salad-Organization": SALAD_ORGANIZATION,
    "Salad-Project": SALAD_PROJECT,
    "Content-Type": "application/json"
}

for job in jobs:

    current_time = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S")

    task = {
    "command": "python",
    "arguments": [ "/app/main.py" ],
    #"environment": job,
    "environment": { **job,"TASK_CREATION_TIME":current_time },
    "container_group_id": SALAD_CONTAINER_GROUP_ID,
    "sync": {
        "during": [
        {
          "bucket": job['BUCKET'],
          "prefix": f"{job['PREFIX']}/{job['FOLDER']}",
          "local_path": KELPIE_MANAGED_UPLOAD_FOLDER,
          "direction": "upload"     # Let Kelpie handle the upload only
        }
      ],
    }
    }
    
    response = requests.post(KELPIE_API_URL+ "/jobs", headers=kelpie_headers, json=task) 
    temp = response.json()
    print(json.dumps(temp, indent=4))

    ID = temp["id"]

    with open( os.path.abspath(JOB_HISTORY),'a' ) as f:
        f.write(ID)
        f.write('\n')