# Use an external counter to enforce the queue length
# Can control the queue length accurately

        
from flask import Flask, request, jsonify
import threading
import queue
import time

app = Flask(__name__)

# Queue to hold incoming requests
request_queue = queue.Queue()

# Counter to track the queue length accurately
current_queue_length = 0 
queue_length_lock = threading.Lock() # The lock to access the global resource

# Reject requests if there is a backlog
MAX_QUEUE_LENGTH = 8

PROCESS_INTERVAL = 1     # Group the incoming requests every PROCESS_INTERVAL second for batched inference
BATCH_SIZE = 4           # Batched inference: process BATCH_SIZE requests at a time

# Simulated batch processing function
def process_batch(batch):
    time.sleep(2)
    try:
        for req_data, _, result in batch: # Simulate the batch processing
            result.append(req_data * req_data) 
        print(f"Processed a batch of {len(batch)} requests.",flush=True)
    except Exception as e:
        # result will be empty in this case
        print("Error processing batch:", e)

    for _ , condition, _ in batch:        # Notify the waiting threads
        try:
            with condition:
                condition.notify()
        except Exception as e:
            # the condition will be invalid if the client timeouts
            print("Client timeout error:", e)
            pass

# Background thread to group and process requests in batches
def batch_processor():
    while True:
        batch = []
        try:
            # Group the incoming request for a batch or until the interval elapses
            while len(batch) < BATCH_SIZE:
                req_data, condition, result = request_queue.get(timeout = PROCESS_INTERVAL)
                batch.append( (req_data, condition, result) )
        except queue.Empty:
            # PROCESS_INTERVAL Timeout - process whatever we have so far
            pass

        if batch:
            process_batch(batch)
            batch.clear()

@app.route('/predict', methods=['POST'])
def predict():
    global current_queue_length

    req_data = request.json.get("data")
    if req_data == None:
        return jsonify({"error": "Invalid request"}), 400
    
    with queue_length_lock:
        if current_queue_length >= MAX_QUEUE_LENGTH:
            return jsonify({"error": "too many requests"}), 400

    condition = threading.Condition()
    result = [] # to keep the result
        
    with queue_length_lock:
        request_queue.put( (req_data, condition, result) )
        current_queue_length += 1

    with condition:
        if not condition.wait(timeout=3):  # Block until notified by batch_processor, avoid indefinitely blocking
            with queue_length_lock:
                current_queue_length -= 1
            return jsonify({"error": "Processing timed out"}), 500    

    with queue_length_lock:
        current_queue_length -= 1
        
    if len(result) == 0:
        return jsonify({"error": "Error processing"}), 500    
    else:
        return jsonify({"result": result[0]}), 200


@app.route('/health_check', methods=['GET'])
def health_check():
    status = "busy" if current_queue_length >= MAX_QUEUE_LENGTH else "ready"
    return jsonify({"status": status}), 200

if __name__ == "__main__":
    # A daemon thread is a background thread that will automatically terminate when all non-daemon (main) threads have completed.
    threading.Thread(target=batch_processor, daemon=True).start()
    #app.run(debug=True,host="0.0.0.0", port="8000",threaded=True)
    app.run(debug=True,host="::", port="8000",threaded=True)
    