import os
import time
import subprocess
import shutil
import threading
import uuid
import queue
from dotenv import load_dotenv
load_dotenv()


g_upload_error = 0
g_current_queue_length = 0 
g_total_size = 0
g_total_number = 0

upload_task_queue = queue.Queue()
queue_length_lock = threading.Lock() 


DATA_SIZE         =  int(os.getenv("SIZE", "1")) # MiB


# Access to the Cloudflare R2 
cloudflare_url    = os.getenv("CLOUDFLARE_ENDPOINT_URL", "")
cloudflare_region = os.getenv("CLOUDFLARE_REGION", "")
cloudflare_id     = os.getenv("CLOUDFLARE_ID", "")
cloudflare_key    = os.getenv("CLOUDFLARE_KEY", "")


# Create the configuration file for rclone
# https://developers.cloudflare.com/r2/examples/rclone/
filename = os.path.expanduser("~")+"/.config/rclone/rclone.conf"
with open(filename,'w') as f:
    f.write("[r2]\n")
    f.write("type = s3\n")
    f.write("provider = Cloudflare\n")
    f.write("access_key_id = {}\n".format(cloudflare_id))
    f.write("secret_access_key = {}\n".format(cloudflare_key))
    f.write("region = {}\n".format(cloudflare_region))
    f.write("endpoint = {}\n".format(cloudflare_url))
    f.write("no_check_bucket = true")


# upload_local_to_cloud=True,  uploading
# upload_local_to_cloud=False, downloading
def Data_Sync(source, bucket, target, upload_local_to_cloud=True, chunk_size_mbype="10M", concurrency="10"):
    t_start  = time.perf_counter()
    if upload_local_to_cloud:
        cmd = f'rclone copyto {source} r2:{bucket}/{target} --s3-chunk-size={chunk_size_mbype} --transfers={concurrency} --ignore-times'
    else:
        cmd = f'rclone copyto r2:{bucket}/{source} {target} --s3-chunk-size={chunk_size_mbype} --transfers={concurrency} --ignore-times'
    #print("executing: " + cmd, flush = True)                                                      
    subprocess.run(cmd, shell=True, check=True, stderr=subprocess.PIPE)
    t_end = time.perf_counter()
    t_duration = round((t_end - t_start), 3) # seco

    if upload_local_to_cloud:
        file_size = round(os.path.getsize(source)/1_000_000, 3)  # MB, not MiB 
    else:
        file_size = round(os.path.getsize(target)/1_000_000, 3)  # MB, not MiB
    
    throughput = round(file_size * 8/t_duration, 3)

    '''
    if upload_local_to_cloud:
        print(f"The file size (MB):{file_size}, the uploading time (second): {t_duration}, the uploading throught (Mbps): {throughput}", flush = True)
    else:
        print(f"The file size (MB):{file_size}, the downloading time (second): {t_duration}, the downloading throught (Mbps): {throughput}", flush = True)
    '''
    
    return file_size, t_duration, throughput


def Data_Async_Upload(source, bucket, target, last, logger):
    global g_current_queue_length

    temp_file   = os.path.join( os.path.dirname(__file__), 'data/' + str(uuid.uuid4()) ) 
    shutil.copyfile(source, temp_file)
    task = { "source": temp_file, "bucket": bucket, "target": target, "logger": logger }   

    if last == False:
        upload_task_queue.put(task)    
        with queue_length_lock: # ----- lock
            g_current_queue_length += 1
    else:
        upload_task_queue.put(task)    
        upload_task_queue.put(None)    
        with queue_length_lock: # ----- lock
            g_current_queue_length += 2


def Get_Uploader_State():
    with queue_length_lock: # ----- lock
        return { "pending":g_current_queue_length, "error":g_upload_error }


def Wait():
    while True:
        temp = Get_Uploader_State()
        print(temp)
        if  temp['pending'] > 0:
            time.sleep(2) 
        else:
            break    


def Uploader():
    global g_upload_error
    global g_current_queue_length   
    global g_total_size 
    global g_total_number

    while True:
        task = upload_task_queue.get()  # Block here
        
        if task == None:
            upload_task_queue.task_done()     # task done     
            with queue_length_lock:
                g_current_queue_length -= 1   
            break
    
        try:
            file_size, t_duration, throughput = Data_Sync(task["source"], task["bucket"], task["target"], upload_local_to_cloud=True)    
            if task["logger"] != None:
                g_total_size = g_total_size + file_size
                file_size = round(file_size,3) 
                g_total_size = round(g_total_size,3)
                g_total_number += 1
                task["logger"].append(f"uploading - size(MB):{file_size}, number:{g_total_number}, total size(MB):{g_total_size}, duration(s):{t_duration}, throughput(Mbps):{throughput}")
        except Exception as e:
            print(40 * "U" + " The UL thread: " + str(e), flush=True)
            g_upload_error += 1
        os.remove( task['source'] )
    
        upload_task_queue.task_done()     # task done     
        with queue_length_lock:
            g_current_queue_length -= 1   

    print(40 * "U" + " The UL thread: end", flush=True)


ul_thread = threading.Thread(target=Uploader, args=())
ul_thread.start()


cmd = f'dd if=/dev/zero of={DATA_SIZE}MiB.file bs=1M count={DATA_SIZE}'
print("executing: " + cmd, flush = True)                                                      
subprocess.run(cmd, shell=True, check=True, stderr=subprocess.PIPE)
test_file_name =  f'{DATA_SIZE}MiB.file'
