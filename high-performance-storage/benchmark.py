from config import Initial_Check, Create_File, Data_Sync, Data_Remove
from config import  SALAD_MACHINE_ID, BUCKET, FOLDER, SIZE
import os
import json
from datetime import datetime, timezone

g_environment = Initial_Check()
print(g_environment)    

local_file = Create_File(SIZE) # MiB
cloud_file = FOLDER+f"/{SALAD_MACHINE_ID}/"+local_file

file_size, t_duration, throughput = Data_Sync(local_file, BUCKET, cloud_file, upload_local_to_cloud=True,  chunk_size_mbype="10M", concurrency="10") # 10 MiB
g_environment.update( {'ul_size(MB)': file_size, 'ul_duration(s)':t_duration,'ul_throughput(Mbps)':throughput} )

file_size, t_duration, throughput = Data_Sync(cloud_file, BUCKET, local_file, upload_local_to_cloud=False, chunk_size_mbype="10M", concurrency="10") # 10 MiB
g_environment.update( {'dl_size(MB)': file_size, 'dl_duration(s)':t_duration,'dl_throughput(Mbps)':throughput} )

now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") # Go-live time
g_environment.update( {'UTC Time-End': now } ) 
                       
Data_Remove(BUCKET,cloud_file)
Data_Remove("",    local_file)


local_file = f"{SALAD_MACHINE_ID}.txt"
with open(os.path.abspath(local_file), 'w') as f:
        f.write(json.dumps(g_environment))

cloud_file = FOLDER+"/results/"+local_file 
Data_Sync(local_file , BUCKET, cloud_file , upload_local_to_cloud=True, chunk_size_mbype="10M", concurrency="10")

Data_Remove("",    local_file)

print(g_environment)    