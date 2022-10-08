import time
import pandas as pd
import statistics
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm
from datetime import datetime
from kubernetes import client, config, utils, watch

config.load_kube_config()
watch = watch.Watch()
api_ApiClient = client.ApiClient()
api_CoreV1Api = client.CoreV1Api()
api_AppsV1Api = client.AppsV1Api()

data = []
node_list = api_CoreV1Api.list_node()

# ************** time measurement function **************


def time_measurement():
    print("Time Measurement RUNS")
    for event in watch.stream(func=api_CoreV1Api.list_namespaced_pod,
                              namespace="default",
                              timeout_seconds=50):
        if event["object"].metadata.deletion_timestamp != None and event["object"].status.phase == 'Running':
            end_time = time.time()
            state = "Terminating"
        else:
            state = str(event["object"].status.phase)
            if (state == "Running"):
                start_time = time.time()
                print("New Pod", event["object"].metadata.name, "runs at: ",
                      datetime.fromtimestamp(start_time).strftime("%H:%M:%S:%f"), "in node: ", event["object"].spec.node_name)
        if (state == "Terminating"):
            print("Pod", event["object"].metadata.name, "terminates at: ",
                  datetime.fromtimestamp(end_time).strftime("%H:%M:%S:%f"), "in node: ", event["object"].spec.node_name)
            mig_time = round(end_time-start_time, 5)*1000
            print("Migration time is: ", mig_time, " [ms]")
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


def calculate_data():
    data.sort()
    mean = round(statistics.mean(data), 5)
    std = round(statistics.stdev(data), 5)
    median = round(statistics.median(data), 5)
    norm_dist = norm.pdf(data, mean, std)

    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()
    fit = norm.pdf(data, mean, std)

    plt.plot(data, fit, '-', linewidth=2, marker='o')
    plt.ylabel('density')
    plt.xlabel('migraion time[ms]')

    plt.grid(color='black', linestyle='--', linewidth=0.2)

    print('Mean: ', mean, '\nMedian: ', median, '\nstd: ', std)

    ax1.hist(data, bins=20, color='gray')
    plt.axvline(mean, color='red', label='Mean')
    plt.axvline(median, color='yellow', label='Median')
    plt.axvline(std, color='blue', label='std')
    ax1.set_ylabel('Frequency')
    plt.legend()

    plt.savefig('chart.png')

#    df = pd.DataFrame({
#      'data': data,
#      'mean': mean,
#      'std': std})
#    df.plot()
#    plt.savefig('mean_std.png')

    with open("results.txt", "a") as f:
        f.write("Collected Data: " + str(data) + "\n")
        f.write("Mean of the Value: " + str(mean) + "\n")
        f.write("Median of the Value: " + str(median) + "\n")
        f.write("Standard Deviation: " + str(std) + "\n")
        f.write("Normal Distribution: " + str(norm_dist) + "\n")
        f.write("-------------------------------------" + "\n")


# ************** main function **************
def main():
    remove_label_node()
    time.sleep(2)
    for x in range(0, 50):
        print("**************  Iterate ", x, "*****************")
        create_deployment('./simple-depl-nginx.yaml')
        time.sleep(2)
        add_label_node()
        add_nodeAffinity()
        time_measurement()
        time.sleep(2)
        api_AppsV1Api.delete_namespaced_deployment(
            name="nginx-deployment", namespace="default")
        remove_label_node()
        time.sleep(2)

    calculate_data()


if __name__ == '__main__':
    main()
