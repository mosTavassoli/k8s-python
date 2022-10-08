from kubernetes import client, config, watch


config.load_kube_config()
k8s_client = client.ApiClinet()
yaml_file = ""


v1 = client.CoreV1Api()
count = 10
w = watch.Watch()

for event in w.stream(v1.list_namespaced_pod("default"), timeout_seconds=10):
    print("Event: %s %s %s" % (
        event["type"],
        event["object"].kind,
        event["object"].metadata.name
    ))
    count -= 1
    if not count:
        w.stop()
print("Finished pod stream")

podlist = v1.list_namespaced_pod("default")
for item in podlist.items:
    pod = v1.read_namespaced_pod_status(
        namespace="default", name=item.metadata.name)
    print("%s\t%s\t" % (item.metadata.name, item.metadata.namespace))
    print(pod.status.phase)
    assert(pod.status.phase == "Running")


watch = kubernetes.watch.Watch()
core_v1 = k8s.CoreV1Api()
for event in watch.stream(func=core_v1.list_namespaced_pod, namespace=namespace, label_selector=label, timeout_seconds=60):
    if event["object"].status.phase == "Running":
        watch.stop()
        end_time = time.time()
        logger.info("%s started in %0.2f sec", full_name, end_time-start_time)
        break
    # event.type: ADDED, MODIFIED, DELETED
    if event["type"] == "DELETED":
        # Pod was deleted while we were waiting for it to start.
        logger.debug("%s deleted before it started", full_name)
        watch.stop()
        return
