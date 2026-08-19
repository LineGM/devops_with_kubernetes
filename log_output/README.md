# Log output

The application generates a UUID once at startup and prints that same value with
a new UTC timestamp every five seconds.

## Run locally

Python 3.11 or newer is recommended. The application has no third-party
dependencies.

```bash
python3 app/main.py
```

Stop it with `Ctrl+C`.

## Deploy to a local k3d cluster

The commands below assume that Docker, kubectl, k3d, and a running k3d cluster
named `k3s-default` are available.

Build the image and import it into the cluster:

```bash
docker build -t log-output:1.3 .
k3d image import log-output:1.3 --cluster k3s-default
```

Create the Deployment and wait for its Pod:

```bash
kubectl apply -f manifests/deployment.yaml
kubectl rollout status deployment/log-output
```

Confirm that the application is running:

```bash
kubectl logs -f deployment/log-output
```

The output should look like this; the UUID remains unchanged until the
container restarts:

```text
2020-03-30T12:15:17.705Z: 8523ecb1-c716-4cb6-a044-b9e83bb98e43
2020-03-30T12:15:22.705Z: 8523ecb1-c716-4cb6-a044-b9e83bb98e43
```

Remove the Deployment when it is no longer needed:

```bash
kubectl delete -f manifests/deployment.yaml
```

If the cluster has a different name, replace `k3s-default` in the import
command. You can list cluster names with `k3d cluster list`.
