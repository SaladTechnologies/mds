import threading
import requests
import time

SERVER_IP_PORT = "localhost:8000"

def inference(text,num):
    url = f"http://{SERVER_IP_PORT}/predict"
    temp = {"data": num}
    response = requests.post(url, json=temp)
    print(temp, response.json())

def health_check(text,num):
    url = f"http://{SERVER_IP_PORT}/health_check"
    time.sleep(num)
    response = requests.get(url)
    print(response.json())

def thead_test(inference_num, health_check_num):
    print("---------------------------------------------------> Thread Test")
    my_threads = []  # keep all the child threads

    for i in range(inference_num):
        temp = threading.Thread(target=inference, args=("inference" + str(i),i) )  
        my_threads.append(temp)

    for i in range(health_check_num):
        temp = threading.Thread(target=health_check, args=("health_check" + str(i),i) ) 
        my_threads.append(temp)

    for i in range(inference_num + health_check_num):
        my_threads[i].start()  # start each child thread

    for i in range(inference_num + health_check_num):
        my_threads[i].join()  # the main thread is waiting here

thead_test(9,4)