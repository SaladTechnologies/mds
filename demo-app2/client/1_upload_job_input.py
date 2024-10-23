from config import JOB_NUMBER, BUCKET_NAME, REMOTE_FOLDER
from config import LOCAL_JOB_DIR
from config import s3
import os

'''
Assume you have a few jobs with their inputs stored in the local_jobs folder;
First upload all job inputs to cloud storage.

├── local_jobs
│   ├── job0
│   │   └── input.txt
|   |
│   ├── job1
│   │   └── input.txt
|   |
│   ├── job2
│   │   └── input.txt
|   |
│   └── job3
│       └── input.txt

'''

for i in range(JOB_NUMBER):

    if i == 2: # to generate a error
        continue 
    
    source = os.path.abspath( f"{LOCAL_JOB_DIR}/job{i}/input.txt" )
    target =                  f"{REMOTE_FOLDER}/job{i}/input.txt"
    
    temp = s3.upload_file(source, BUCKET_NAME, target) 
    print(source," -> ", target)