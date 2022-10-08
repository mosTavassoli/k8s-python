import sys
import pandas as pd
import math
import time
from dateutil import parser
from datetime import datetime, timedelta
from kubernetes import client, config
from kubernetes.client.rest import ApiException
c_temp = []
s_temp = []
current_time = sys.argv[1]
# current_time = datetime.now().time().strftime('%I:%M %p')
print(current_time)
current_time = parser.parse(current_time)
print(current_time)


# Configs can be set in Configuration class directly or using helper utility
config.load_kube_config()

v1 = client.CoreV1Api()
ret = v1.list_pod_for_all_namespaces(watch=False)
count = 0
for i in ret.items:
    if i.metadata.namespace == 'default':
        count = count+1
        api_instance = client.CoreV1Api()

        api_response = api_instance.read_namespaced_pod(
            name=i.metadata.name, namespace='default')
        c_time = api_response.status.start_time
        c_time = c_time.replace(tzinfo=None)
        c_time = c_time+timedelta(hours=1)
        c_duration = c_time-current_time
        c_temp.append(c_duration.total_seconds())

        s_time = api_response.status.container_statuses[0].state.running.started_at
        s_time = s_time.replace(tzinfo=None)
        s_time = s_time+timedelta(hours=1)
        s_duration = s_time-current_time
        s_temp.append(s_duration.total_seconds())

c_temp.sort(reverse=True)
s_temp.sort(reverse=True)
print(c_temp[0])
print(s_temp[0])
print(current_time)
a = []
a.append(count)
a.append(c_temp[0])
a.append(s_temp[0])
with open('results_kube.txt', 'a') as f:
    for i in a:
        f.write(str(i)+" ")
    f.write("\n")
print(s_temp)
`
