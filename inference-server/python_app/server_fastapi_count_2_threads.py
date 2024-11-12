# Main thread(async), I/O 
# Batch-processing thread(sync), GPU inference

# Batch-processing thread(sync) ---- thread.event ---- Main thread(async), not use asyncio.event
# Batch-processing thread(sync) ---- janus.queue  ---- Main thread(async), not use thread.queue and asyncio.queue

# Queue.qsize() might be close, but not accurate in the multihtreading environment.
# Use an external counter to enforce the queue length

# GPU inference (typically done using frameworks like TensorFlow or PyTorch) may not
# be fully async-compatible because it often involves blocking operations on the GPU. 
# In such cases, the async function might not speed up the GPU inference but can still
# improve overall application responsiveness when handling other tasks concurrently.

# The list created by Thread A is passed to Thread B through a queue.
# After Thread A exits, Thread B has a reference to the list and can use or modify it.

from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from pydantic import BaseModel
import asyncio
import uvicorn
import threading
import janus
import time

# Configuration for queue length and batch processing
MAX_QUEUE_LENGTH = 8
PROCESS_INTERVAL = 1     # Process batch every 1 second
BATCH_SIZE = 4           # Number of requests to process per batch

# Asynchronous lock for queue length tracking
queue_length_lock = asyncio.Lock()
current_queue_length = 0

# Janus queue to hold incoming requests
request_queue = None

# Request and Response model for FastAPI
class RequestData(BaseModel):
    data: int

# Simulated sync batch processing function
def process_batch(batch):
    time.sleep(2)  # Simulate processing time
    try:
        for req_data, _, result in batch:
            result.append(req_data * req_data)  # Simulate batch-processing
        print(f"Processed a batch of {len(batch)} requests.", flush=True)
    except Exception as e:
        print("Error processing batch:", e)

    # Notify all waiting requests after processing
    for _, result_event, _ in batch:
        try:
            result_event.set()
        except Exception as e:
            # the event will be invalid if the client timeouts
            print("Client timeout error:", e)
            pass

# Background thread  to process requests in batches
def batch_processor():
    while True:
        batch = []
        try:
            # Collect a batch or wait for PROCESS_INTERVAL timeout
            while len(batch) < BATCH_SIZE:
                req_data, result_event, result = request_queue.sync_q.get(timeout = PROCESS_INTERVAL)
                batch.append((req_data, result_event, result))
        except Exception as e:
            # Timeout - process the collected batch
            pass

        if batch:
            process_batch(batch)
            batch.clear()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global request_queue
    # A event loop should be ready before this initialization
    request_queue = janus.Queue() # Initialize a Janus queue for thread safety

    # Run batch_processor in a separate thread to prevent blocking the main thread
    thread = threading.Thread(target=batch_processor, daemon=True)
    thread.start()
    yield
    #thread.join()  # Wait for background thread to finish processing
    print("Application lifespan ended.")

app = FastAPI(lifespan=lifespan)

@app.post("/predict")
async def predict(request_data: RequestData):
    global current_queue_length

    # Check if the queue has reached the maximum length
    async with queue_length_lock:
        if current_queue_length >= MAX_QUEUE_LENGTH:
            raise HTTPException(status_code=400, detail="Too many requests")
    
        # Prepare the request and add it to the queue
        result_event = threading.Event()  # Use a thread-safe Event
        result = []
        await request_queue.async_q.put((request_data.data, result_event, result))
        current_queue_length += 1

    # Wait for the processing result in a non-blocking way
    # await asyncio.get_running_loop().run_in_executor(None, result_event.wait)
    try:
        await asyncio.wait_for( asyncio.get_running_loop().run_in_executor(None, result_event.wait), timeout=3 )
    except asyncio.TimeoutError:
        async with queue_length_lock:
            current_queue_length -= 1
        raise HTTPException(status_code=500, detail="Processing timed out")
    
    async with queue_length_lock:
        current_queue_length -= 1

    # Return the processed result or error if processing failed
    if not result:
        raise HTTPException(status_code=500, detail="Error processing request")
    return {"result": result[0]}

@app.get("/health_check")
async def health_check():
    async with queue_length_lock:
        status = "busy" if current_queue_length >= MAX_QUEUE_LENGTH else "ready"
    return {"status": status}

if __name__ == "__main__":
    #uvicorn.run("server_fastapi_count_2_threads:app", host="0.0.0.0", port=8000, reload=True)
    uvicorn.run("server_fastapi_count_2_threads:app", host="::", port=8000, reload=True)
