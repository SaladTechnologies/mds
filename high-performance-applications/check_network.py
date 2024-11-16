import speedtest
from pythonping import ping


# Test network bandwdith
def network_test():
    print("Test the network speed ....................", flush=True)
    try:
        speed_test = speedtest.Speedtest()
        bserver = speed_test.get_best_server()
        dlspeed = int(speed_test.download() / (1000 * 1000))  # Convert to Mbps, not Mib
        ulspeed = int(speed_test.upload() / (1000 * 1000))  # Convert to Mbps, not Mib
        latency = bserver['latency'] # the latency to the test server
        country = bserver['country'] 
        location = bserver['name']
    except Exception as e:  
        return "", "", 99999, 0, 0
    return country, location, latency, dlspeed, ulspeed    


# Test network latency
# Only the root user can run this code - ok if running inside containers
def ping_test(tCount=10):
    print("Test the latency ....................", flush=True)
    try:
        print("To: ec2.us-east-1.amazonaws.com")
        temp = ping('ec2.us-east-1.amazonaws.com', interval=1, count=tCount, verbose=True)
        latency_useast1 = temp.rtt_avg_ms      
        print("To: ec2.eu-central-1.amazonaws.com")  
        temp = ping('ec2.eu-central-1.amazonaws.com', interval=1, count=tCount,verbose=True)
        latency_eucentral1 = temp.rtt_avg_ms
    except Exception as e:  
        return 99999,99999
    return latency_useast1, latency_eucentral1

