# Todo app

A minimal web server for the DevOps with Kubernetes course project. The server
reads its listening port from the `PORT` environment variable and uses port
`3000` by default.

## Run locally

Python 3.11 or newer is recommended. The application has no third-party
dependencies.

```bash
PORT=8080 python3 app/main.py
```

The startup output is:

```text
Server started in port 8080
```

You can then check the server locally with `curl http://localhost:8080` and stop
it with `Ctrl+C`.

## Deploy to a local k3d cluster

The commands below assume that Docker, kubectl, k3d, and a running k3d cluster
named `k3s-default` are available.

Build the image and import it into the cluster:

```bash
docker build -t todo-app:1.5 .
k3d image import todo-app:1.5 --cluster k3s-default
```

Create the Deployment and wait for its Pod:

```bash
kubectl apply -f manifests/deployment.yaml
kubectl rollout status deployment/todo-app
```

Confirm that the configured port was used:

```bash
kubectl logs deployment/todo-app
```

Forward local port `3003` to the application's port inside the cluster:

```bash
kubectl port-forward deployment/todo-app 3003:3000
```

Open <http://localhost:3003> in a browser. Stop port forwarding with `Ctrl+C`.
Port forwarding is intended for local development and debugging; the
application is not exposed through a Kubernetes Service yet.

Remove the Deployment when it is no longer needed:

```bash
kubectl delete -f manifests/deployment.yaml
```

If the cluster has a different name, replace `k3s-default` in the import
command. You can list cluster names with `k3d cluster list`.
