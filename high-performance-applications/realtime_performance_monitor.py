from imds_reallocate import Reallocate
import random
import time

# Transcription Performance
# RTF - Realtime Factor, audio length divided by processing time
# the effective measurement of transcription performance

# Adopt the Adaptive Algorithm
# RTF > 100, super node, you may increase the max length of local queue
# RTF 80, normal node 
# RTF 40, low-performing node, you may decrease the max length of local queue
# RTF < 20, bad node, reallocate


Number_of_RTF = 0
Sum_RTF = 0

MONITOR_INTERVAL = 300  # 5 minutes, Interval of Monitoring 

def mock_inference():
    time.sleep(1)
    return random.randint(0,150)

pStart = time.perf_counter()
while True:  

    rtf = mock_inference() # Run an inference task and get its performance

    Number_of_RTF = Number_of_RTF + 1 
    Sum_RTF       = Sum_RTF + rtf

    pEnd = time.perf_counter()

    if (pEnd - pStart) >= MONITOR_INTERVAL:  # Calculate the performance during the interval

        Average_RTF = Sum_RTF / Number_of_RTF

        if Average_RTF < 20:
            Reallocate(local=True, reason="Bad node!") # Reallocate
        elif Average_RTF < 40:
            print("Low-performing node!")
            # May adjust some settings to better use the node,
            # such as decreasing the maximum length of local queue
            pass
        elif Average_RTF > 100:
            print("Super node!")
            # May adjust some settings to better use the node,
            # such as increasing the maximum length of local queue
            pass
        else:
            print("Normal node!")
            pass

        pStart = time.perf_counter()