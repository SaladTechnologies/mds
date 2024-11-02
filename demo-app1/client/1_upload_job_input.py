from config import TASK_NUMBER, BUCKET_NAME, REMOTE_FOLDER
from config import LOCAL_JOB_DIR
from config import s3
import os

'''
Assume you have 3 jobs with their inputs stored in the local_jobs folder;
First upload all job inputs to cloud storage.

─── local_jobs
    ├── job0
    │   ├── input
    │   │   └── input.txt
    │   └── output
    ├── job1
    │   ├── input
    │   │   └── input.txt
    │   └── output
    └── job2
        ├── input
        │   └── input.txt
        └── output
'''

for i in range(TASK_NUMBER):
    source = os.path.abspath( f"{LOCAL_JOB_DIR}/job{i}/input/input.txt" )
    target =                  f"{REMOTE_FOLDER}/job{i}/input/input.txt"
    
    try:
        temp = s3.upload_file(source, BUCKET_NAME, target) 
        print(source," -> ", target)
    except Exception as e:
        pass  