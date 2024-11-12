# The main thread handles everything

# GPU inference (typically done using frameworks like TensorFlow or PyTorch) may not
# be fully async-compatible because it often involves blocking operations on the GPU. 
# In such cases, the async function might not speed up the GPU inference but can still
# improve overall application responsiveness when handling other tasks concurrently.


from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from pydantic import BaseModel
import asyncio
import uvicorn

# Configuration for queue length and batch processing
MAX_QUEUE_LENGTH = 8
PROCESS_INTERVAL = 1     # Process batch every 1 second
BATCH_SIZE = 4           # Number of requests to process per batch

# Asynchronous queue to hold incoming requests
request_queue = asyncio.Queue(maxsize=MAX_QUEUE_LENGTH)

# Request and Response model for FastAPI
class RequestData(BaseModel):
    data: int

# Simulated async batch processing function
async def process_batch(batch):
    await asyncio.sleep(2)  # Simulate processing time
    try:
        for req_data, _, result in batch:
            result.append(req_data * req_data)  # Simulate processing
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

# Background coroutine to process requests in batches
async def batch_processor():
    while True:
        batch = []
        try:
            while len(batch) < BATCH_SIZE:
                req_data, result_event, result = await asyncio.wait_for(
                    request_queue.get(), timeout=PROCESS_INTERVAL)
                batch.append((req_data, result_event, result))
        except asyncio.TimeoutError:
            pass  # Timeout reached - process the batch

        if batch:
            await process_batch(batch)
            batch.clear()

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(batch_processor())
    yield
    print("Application lifespan ended")

app = FastAPI(lifespan=lifespan)

@app.post("/predict")
async def predict(request_data: RequestData):
    # Check if the queue has reached the maximum length
    if request_queue.full():
        raise HTTPException(status_code=400, detail="Too many requests")

    # Prepare the request and add it to the queue
    result_event = asyncio.Event()  # Event to signal processing completion
    result = []
    await request_queue.put((request_data.data, result_event, result))

    # Wait asynchronously for the processing result with a timeout for safety
    try:
        await asyncio.wait_for(result_event.wait(), timeout=3)  # Non-blocking wait for result
    except asyncio.TimeoutError:
        raise HTTPException(status_code=500, detail="Processing timed out")

    # Return the processed result or error if processing failed
    if not result:
        raise HTTPException(status_code=500, detail="Error processing request")
    return {"result": result[0]}

@app.get("/health_check")
async def health_check():
    status = "busy" if request_queue.full() else "ready"
    return {"status": status}

if __name__ == "__main__":
    #uvicorn.run("server_fastapi_maxsize_1_thread:app", host="0.0.0.0", port=8000, reload=True)
    uvicorn.run("server_fastapi_maxsize_1_thread:app", host="::", port=8000, reload=True)
