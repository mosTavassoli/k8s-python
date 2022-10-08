import time
from datetime import datetime
from kubernetes import client, config, utils, watch

config.load_kube_config()
watch = watch.Watch()
api_ApiClient = client.ApiClient()
api_CoreV1Api = client.CoreV1Api()
api_AppsV1Api = client.AppsV1Api()


# ************** time measurement function **************
def time_measurement():
    for event in watch.stream(func=api_CoreV1Api.list_namespaced_pod,
                              namespace="default",
                              timeout_seconds=500):
        print("Watching...")
        if event["object"].metadata.deletion_timestamp != None and event["object"].status.phase == 'Running':
            state = 'Terminating'
        else:
            state = str(event["object"].status.phase)
        if (state == "Terminating"):
            end_time = time.time()
            print("Pod", event["object"].metadata.name, "terminates at: ",
                  end_time, "in node: ", event["object"].spec.node_name)
            watch.stop()
        elif (state == "Running"):
            start_time = time.time()
            print("New Pod", event["object"].metadata.name, "runs at: ",
                  start_time, "in node: ", event["object"].spec.node_name)

    print("Migration time is: ", datetime.fromtimestamp(
        end_time - start_time).strftime("%H:%M:%S:%f [MS]"))


# ************* add label node **************
def add_label_node():
    body = {
        "metadata": {
            "labels": {
                "node": "migration",
            }
        }
    }

    ret = api_CoreV1Api.list_namespaced_pod(namespace="default")
    for i in ret.items:
        print(i.spec.node_name)
        worker_node = i.spec.node_name
    # Listing the cluster nodes
    node_list = api_CoreV1Api.list_node()
    # Patching the node labels
    for node in node_list.items:
        if (worker_node == "worker-1"):
            api_CoreV1Api.patch_node("worker-2", body)
        else:
            api_CoreV1Api.patch_node("worker-1", body)


# ************* remove label node **************
def remove_label_node():
    body = {
        "metadata": {
            "labels": {
                "node": "none",
            }
        }
    }

    node_list = api_CoreV1Api.list_node()
    # Patching the node labels
    for node in node_list.items:
        api_CoreV1Api.patch_node(node, body)


# ************** create deployment function **************
def create_deployment(name):
    utils.create_from_yaml(api_ApiClient, name, verbose=False)


# ************** create addNodeAffinity function **************
def add_nodeAffinity():
    deployment = api_AppsV1Api.read_namespaced_deployment(
        name='nginx-deployment', namespace='default')
    terms = client.models.V1NodeSelectorTerm(
        match_expressions=[
            {'key': 'node',
             'operator': 'In',
             'values': ["migration"]}
        ]
    )
    node_selector = client.models.V1NodeSelector(node_selector_terms=[terms])
    node_affinity = client.models.V1NodeAffinity(
        required_during_scheduling_ignored_during_execution=node_selector
    )
    affinity = client.models.V1Affinity(node_affinity=node_affinity)
    # replace affinity in the deployment object
    deployment.spec.template.spec.affinity = affinity
    # finally, push the updated deployment configuration to the API-server
    api_AppsV1Api.replace_namespaced_deployment(name=deployment.metadata.name,
                                                namespace=deployment.metadata.namespace,
                                                body=deployment)


# ************** main function **************
def main():
    create_deployment('./simple-depl-nginx.yaml')
    time.sleep(5)
    add_label_node()
    time.sleep(5)
    add_nodeAffinity()
    time_measurement()


if __name__ == '__main__':
    main()
