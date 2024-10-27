from config import JOB_NUMBER, BUCKET_NAME, REMOTE_FOLDER
import requests

for i in range(JOB_NUMBER):
    print ( f"--------------------------------------------> job{i}" )

    print ( "-----> input:" )
    url = f"https://salad-public-{BUCKET_NAME}.com/{REMOTE_FOLDER}/job{i}/input.txt"
    response = requests.get(url)
    if response.status_code == 200:
        print(response.text, flush=True)

    print ( "-----> state:" )
    url = f"https://salad-public-{BUCKET_NAME}.com/{REMOTE_FOLDER}/job{i}/state.txt"
    response = requests.get(url)
    if response.status_code == 200:
        print(response.text, flush=True)

    print ( "-----> logs:" )
    url = f"https://salad-public-{BUCKET_NAME}.com/{REMOTE_FOLDER}/job{i}/logs.txt"
    response = requests.get(url)
    if response.status_code == 200:
        print(response.text, flush=True)

    print ( "-----> output:" )
    url = f"https://salad-public-{BUCKET_NAME}.com/{REMOTE_FOLDER}/job{i}/output.txt"
    response = requests.get(url)
    if response.status_code == 200:
        print(response.text, flush=True)
