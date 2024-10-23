from config import JOB_NUMBER, BUCKET_NAME, REMOTE_FOLDER
from config import s3

for i in range(JOB_NUMBER):
    target = f"{REMOTE_FOLDER}/job{i}/input.txt"
    temp = s3.delete_object(Bucket=BUCKET_NAME,Key=target)
    print(temp)

    target = f"{REMOTE_FOLDER}/job{i}/state.txt"
    temp = s3.delete_object(Bucket=BUCKET_NAME,Key=target)
    print(temp)
    
    target = f"{REMOTE_FOLDER}/job{i}/logs.txt"
    temp = s3.delete_object(Bucket=BUCKET_NAME,Key=target)
    print(temp)
    
    target = f"{REMOTE_FOLDER}/job{i}/output.txt"
    temp = s3.delete_object(Bucket=BUCKET_NAME,Key=target)
    print(temp)