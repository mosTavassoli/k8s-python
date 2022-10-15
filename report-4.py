import time
import numpy as np
from datetime import datetime
from kubernetes import client, config, utils, watch


config.load_kube_config()
watch = watch.Watch()
api_ApiClient = client.ApiClient()
api_CoreV1Api = client.CoreV1Api()
api_AppsV1Api = client.AppsV1Api()
node_list = api_CoreV1Api.list_node()
data = []

# ************** time measurement function **************


def time_measurement():
    print("Time Measurement RUNS")
    for event in watch.stream(func=api_CoreV1Api.list_namespaced_pod,
                              namespace="default",
                              timeout_seconds=50):
        if event["object"].metadata.deletion_timestamp != None and event["object"].status.phase == 'Running':
            end_time = datetime.now()
            state = "Terminating"
        else:
            state = str(event["object"].status.phase)
            if (state == "Running"):
                start_time = datetime.now()
                print("New Pod", event["object"].metadata.name, "runs at: ",
                      start_time, "in node: ", event["object"].spec.node_name)
        if (state == "Terminating"):
            print("Pod", event["object"].metadata.name, "terminates at: ",
                  end_time, "in node: ", event["object"].spec.node_name)
            mig_time = (end_time-start_time).total_seconds() * pow(10, 3)
            print("Migration time is: ",
                  mig_time, "[ms]")
            data.append(mig_time)
            watch.stop()


# ************* add label node **************
def add_label_node():
    print("Add_Label RUNS")
    body = {
        "metadata": {
            "labels": {
                "node": "migration",
            }
        },
        "spec": {
            "taints": [{
                'effect': 'NoSchedule',
                'key': 'node',
                'value': 'migration',
                'operator': 'Equal'
            }]
        }
    }

    ret = api_CoreV1Api.list_namespaced_pod(namespace="default")
    for i in ret.items:
        # print(i.spec.node_name)
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
    print("Remove Label RUNS")
    label_body = {
        "metadata": {
            "labels": {
                "node": None,
            }
        }
    }

    taint_body = {
        "spec": {
            "taints": None
        }
    }

    node_list = api_CoreV1Api.list_node()
    # Patching the node labels
    for node in node_list.items:
        labels = node.metadata.labels
        taints = node.spec.taints
        if (("node", "migration") in labels.items()):
            api_CoreV1Api.patch_node(node.metadata.name, label_body)
        if ("node" in labels):
            if (taints is not None):
                for taint in taints:
                    if (taint.value == "migration"):
                        api_CoreV1Api.patch_node(
                            node.metadata.name, taint_body)

# ************** create deployment function **************


def create_deployment(name):
    utils.create_from_yaml(api_ApiClient, name, verbose=False)


# ************** create addNodeAffinity function **************
def add_nodeAffinity():
    print("Add nodeAffinity RUNS")
    deployment = api_AppsV1Api.read_namespaced_deployment(
        name='nginx-deployment', namespace='default')
    terms = client.models.V1NodeSelectorTerm(
        match_expressions=[
            {'key': 'node',
             'operator': 'In',
             'values': ["migration"]}
        ]
    )
    tolerations_term = [
        {
            "effect": "NoSchedule",
            "key": "node",
            "operator": "Equal",
            "value": "migration"
        }
    ]

    node_selector = client.models.V1NodeSelector(node_selector_terms=[terms])
    node_affinity = client.models.V1NodeAffinity(
        required_during_scheduling_ignored_during_execution=node_selector
    )
    affinity = client.models.V1Affinity(node_affinity=node_affinity)
    # replace affinity in the deployment object
    deployment.spec.template.spec.affinity = affinity
    deployment.spec.template.spec.tolerations = tolerations_term
    # finally, push the updated deployment configuration to the API-server
    api_AppsV1Api.replace_namespaced_deployment(name=deployment.metadata.name,
                                                namespace=deployment.metadata.namespace,
                                                body=deployment)
# ----------- Visualization -------------


def confidence_interval(data, rep=100, coeff=1.96):  # default 95%
    data_avg = np.mean(data)
    data_std = np.std(data)
    max_val = data_avg+coeff*data_std/np.sqrt(rep)
    min_val = data_avg-coeff*data_std/np.sqrt(rep)
    return data_avg, data_std, max_val, min_val


def calculate_data():
    data_avg, data_std, max_val, min_val = confidence_interval(data)

    with open("results.txt", "a") as f:
        f.write("Number of Data: " + str(len(data)) + "\n")
        f.write("Collected Data: " + str(data) + "\n")
        f.write("Mean of the Value: " + str(data_avg) + "\n")
        f.write("Standard Deviation: " + str(data_std) + "\n")
        f.write("Confidence Interval, min_value: " + str(min_val) + "\n")
        f.write("Confidence Interval, max_value: " + str(max_val) + "\n")
        f.write("-------------------------------------" + "\n")

# ************** main function **************


def main():
    remove_label_node()
    time.sleep(2)
    for x in range(0, 100):
        print("************** loop ", x, "*****************")
        create_deployment('./nginx-depl.yaml')
        time.sleep(3)
        add_label_node()
        add_nodeAffinity()
        time_measurement()
        time.sleep(2)
        api_AppsV1Api.delete_namespaced_deployment(
            name="nginx-deployment", namespace="default")
        remove_label_node()
        time.sleep(3)

    calculate_data()


if __name__ == '__main__':
    main()
