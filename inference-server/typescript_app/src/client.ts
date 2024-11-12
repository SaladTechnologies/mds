import axios from 'axios'; 
// npm install axios, which includes the type definition file

const SERVER_IP_PORT = "http://localhost:8000";

// async can automatically return a promise object
// Promise<void>，for better readability and maintainability
async function inference(text: string, num: number): Promise<void> {
    try {
        const url = `${SERVER_IP_PORT}/predict`;
        const temp = { data: num };

        // await，wait until the promise is done
        const response = await axios.post(url, temp);
        console.log(`Inference ${text}:`, response.data);
    } catch (error) {
        console.error(`Error in inference ${text}:`, error);
    }
}

async function healthCheck(text: string, num: number): Promise<void> {
    try {
        const url = `${SERVER_IP_PORT}/health_check`;
        
        // await，wait until the promise object is done
        // Delay equivalent to Python's time.sleep()
        await new Promise(resolve => setTimeout(resolve, num * 1000)); 
        
        // await，wait until the promise object is done
        const response = await axios.get(url);
        console.log(`Health Check ${text}:`, response.data);
    } catch (error) {
        console.error(`Error in health check ${text}:`, error);
    }
}

async function currentTest(inferenceNum: number, healthCheckNum: number): Promise<void> {
    console.log("---------------------------------------------------> Thread Test");

    // Create an array with inferenceNum x inference(promise)
    // { length: inferenceNum } -> { "length": inferenceNum }
    // Two inputs for Array.from: { "length": inferenceNum } and the callback function
    // _，current element（not existed in this scenario）
    // xx，current index
    const inferencePromises = Array.from({ length: inferenceNum }, (_, xx) =>
        inference(`inference${xx}`, xx)
    );

    // Create an array with healthCheckNum x healthcheck(promise)
    const healthCheckPromises = Array.from({ length: healthCheckNum }, (_, yy) =>
        healthCheck(`health_check${yy}`, yy)
    );

    // Start all "threads" concurrently
    await Promise.all([...inferencePromises, ...healthCheckPromises]);

    console.log("All threads completed.");
}

// Run the test
// Only handle the catch(reject), not then(resolve)
currentTest(9, 4).catch( error => console.error("Error in the test:", error)) ;
