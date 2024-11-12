import express, { Request, Response } from 'express';
import bodyParser from 'body-parser';

const app = express();
const PORT = 8000;
const MAX_QUEUE_LENGTH = 8; // Maximum number of requests allowed in the queue

// Middleware to parse JSON request body
app.use(bodyParser.json());

// Type and interface are similar, but type does not support extends and implements.
// Additionally, type can be used to create aliases for primitive types.
type RequestItem = { req: Request; res: Response }; // The element type of array

// Define an empty queue using the RequestItem type
const requestQueue: RequestItem[] = [];             

const BATCH_SIZE = 4;        // Number of requests per batch
const BATCH_INTERVAL = 1000; // Process the queue every 2 seconds

// Function to simulate processing of a request: 
// input - the number in the request, output - square of the number
const processRequest = (req: Request): number => {
    // Assume the number is passed as "data" in the request body
    const value = req.body.data;
    if (typeof value !== 'number') {
        throw new Error("Invalid data value");
    }
    return value * value; // Return the square of the number
};

// Function to process requests in batches
const processQueue = () => {
    if (requestQueue.length === 0) return;

    // Get a batch of requests from the queue
    const batch = requestQueue.splice(0, BATCH_SIZE);

    // Process each request in the batch
    batch.forEach(({ req, res }) => {
        try {
            // Simulate processing the request and generate the result (square of the value)
            const result = processRequest(req);

            // Send the result back as a response for each request
            res.send({ result: result });
        } catch (error: unknown) {
            // In case of an error (like invalid data value), respond with an error message
            if (error instanceof Error) {
                // Now TypeScript knows `error` is an `Error` and has a `message` property
                res.status(400).send({ error: error.message });
            } else {
                // Handle the case where `error` is not an instance of `Error`
                res.status(400).send({ error: "Unknown error occurred" });
            }
        }
    });
};

// Schedule batch processing at regular intervals
// The built-in function by JavaScript，declared through @type/node
setInterval(processQueue, BATCH_INTERVAL);

// Endpoint to receive POST requests
app.post('/predict', (req: Request, res: Response) => {
    // Check if the queue is full
    if (requestQueue.length >= MAX_QUEUE_LENGTH) {
        // Reject the request if the queue is full
        res.status(429).send({ error: "Queue is full. Please try again later." });
    } else {
    // Add request to the queue instead of processing immediately
    requestQueue.push({ req, res });
    console.log(`Request queued for data: ${req.body.data}`); }
}
);

// Health check endpoint
app.get('/health_check', (req: Request, res: Response) => {
    if (requestQueue.length >= MAX_QUEUE_LENGTH) {
        res.send({ status: "busy" }); 
    } else {
        res.send({ status: "ready" }); // Server is ready to accept more requests
    }
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});
