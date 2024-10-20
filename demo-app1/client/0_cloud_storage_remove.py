from config import TASK_NUMBER, BUCKET_NAME, REMOTE_FOLDER
from config import s3

for i in range(TASK_NUMBER):
    target = f"{REMOTE_FOLDER}/job{i}/input/input.txt"
    temp = s3.delete_object(Bucket=BUCKET_NAME,Key=target)
    print(temp)

    target = f"{REMOTE_FOLDER}/job{i}/state/state.txt"
    temp = s3.delete_object(Bucket=BUCKET_NAME,Key=target)
    print(temp)
    
    target = f"{REMOTE_FOLDER}/job{i}/state/logs.txt"
    temp = s3.delete_object(Bucket=BUCKET_NAME,Key=target)
    print(temp)
    
    target = f"{REMOTE_FOLDER}/job{i}/output/output.txt"
    temp = s3.delete_object(Bucket=BUCKET_NAME,Key=target)
    print(temp)