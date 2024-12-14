from config import TASK_NUMBER, BUCKET_NAME, REMOTE_FOLDER
import requests

for i in range(TASK_NUMBER):
    print ( f"----------------------> job{i}" )

    print ( "-----> intput:" )
    url = f"https://salad-public-{BUCKET_NAME}.com/{REMOTE_FOLDER}/job{i}/input/input.txt"
    response = requests.get(url)
    if response.status_code == 200:
        print(response.text, flush=True)

    print ( "-----> state - running data:" )
    url = f"https://salad-public-{BUCKET_NAME}.com/{REMOTE_FOLDER}/job{i}/state/state.txt"
    response = requests.get(url)
    if response.status_code == 200:
        print(response.text, flush=True)

    print ( "-----> state - logs:" )
    url = f"https://salad-public-{BUCKET_NAME}.com/{REMOTE_FOLDER}/job{i}/state/logs.txt"
    response = requests.get(url)
    if response.status_code == 200:
        print(response.text, flush=True)

    print ( "-----> output:" )
    url = f"https://salad-public-{BUCKET_NAME}.com/{REMOTE_FOLDER}/job{i}/output/output.txt"
    response = requests.get(url)
    if response.status_code == 200:
        print(response.text, flush=True)
