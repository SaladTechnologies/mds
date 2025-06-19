import json
from datetime import datetime, timedelta

def parse_time(t):
    return datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
 
def str_to_timedelta(s):
    if 'day' in s:
        days_part, time_part = s.split(', ')
        days = int(days_part.split()[0])
    else:
        days = 0
        time_part = s
    h, m, s = map(int, time_part.split(':'))
    return timedelta(days=days, hours=h, minutes=m, seconds=s)


def events_analysis(mylist):
    sublists = []
    current_sublist = []
    current_machine_id = None

    for event in mylist:
        _, machine_id, event_type = event[0], event[1], event[2]
        if event_type in ("online"): # New Node

            if current_sublist:
                sublists.append(current_sublist)

            current_sublist = [event]
            current_machine_id = machine_id
        else:                         # events from the same Node                      
            if machine_id != current_machine_id:
                print("Error! Should be the same")
            if not current_sublist:
                print("Error! Should not be empty")
            current_sublist.append(event)

    if current_sublist:
        sublists.append(current_sublist)

    return sublists



HISTORY_FILE = "history.txt"

with open(HISTORY_FILE,'r') as f:
    g_History = json.load(f)      


print(g_History["task_creation_time"])
print(g_History["task_completion_time"])
print(g_History["task_duration"])

node_run_list = events_analysis(g_History["task_history"])

print(f"Total Node Runs: {len(node_run_list)}")




# Calculate and print durations
run_time = timedelta(0)
for node_run in node_run_list:
    
    start_time = parse_time(node_run[0][0])
    end_time = parse_time(node_run[-1][0])
    duration = end_time - start_time
    run_time = run_time + duration


    chunk_number = 0
    step_number = 0
    for line in node_run:
        if 'run_chunk' == line[2]:
            chunk_number += 1
            step_number += int(line[3]['chunk_steps'])

    efficiency = step_number / ( duration.total_seconds() )
    
    print(f"ID: {node_run[0][1]}, GPU:{node_run[0][3]['gpu']}, Start: {node_run[0][0]}, End: {node_run[-1][0]}, Duration: {duration}, Chunks: {chunk_number}, Steps: { step_number }, Steps/Second: {efficiency:.2f} steps/sec")

print(run_time)

duration = str_to_timedelta(g_History["task_duration"]) 

print( run_time / duration )