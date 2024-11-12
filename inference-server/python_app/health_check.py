import requests,sys

SERVER_IP_PORT = "localhost:8000"

print('ready' if 'ready' in requests.get(f'http://{SERVER_IP_PORT}/health_check').text else 'non-ready')

sys.exit(0 if 'ready' in requests.get(f'http://{SERVER_IP_PORT}/health_check').text else -1)

# Check the status of previous command
'''
echo $?
0 - success
'''

# Example - the readiness check on SaladCloud
'''
Probe Protocol: exec

Command: python
Argument1: -c
Argument2: import requests,sys;sys.exit(0 if 'READY' in requests.get('http://[::1]:5000/health-check').text else -1)

Initial Delay Seconds: 60
Period Seconds: 10
Timeout Seconds: 5
Success Threshold: 1
Failure Threshold: 3
'''