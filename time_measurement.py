import logging
import time
from datetime import datetime
from kubernetes import client, config, utils,

logging.basicConfig(filename="newfile.log",
                    format='%(asctime)s %(message)s',
                    filemode='w')

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

config.load_kube_config()
k8s_client = client.ApiClient()
yaml_file = './simple-depl-nginx.yaml'
utils.create_from_yaml(k8s_client, yaml_file, verbose=True)

watch = watch.Watch()
core_v1 = client.CoreV1Api()
for event in watch.stream(func=core_v1.list_namespaced_pod,
                          namespace="default",
                          timeout_seconds=60):
    if event["object"].status.phase == "Running":
        watch.stop()
        #end_time = datetime.fromtimestamp(time.time()).replace(tzinfo=None)
        #end_time = datetime.now().time().strftime('%I:%M %p')
        end_time = time.time()
        print(end_time)
        start_time = event["object"].status.start_time.replace(
            tzinfo=None).timestamp()
        print(start_time)
        print(datetime.fromtimestamp(end_time - start_time).strftime("%H:%M:%S"))
        logging.info("%s started in %0.2f sec", end_time-start_time)
        break
    # event.type: ADDED, MODIFIED, DELETED
    if event["type"] == "DELETED":
        # Pod was deleted while we were waiting for it to start.
        #        logging.debug("%s deleted before it started", full_name)
        watch.stop()
        break
