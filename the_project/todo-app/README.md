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

The commands below assume that Docker, kubectl, and k3d are available. A minimal
local cluster for the application can be created with:

```bash
k3d cluster create --agents 2
```

The application code has not changed since exercise 1.6, so its existing image
tag can be reused. Build the image and import it into the cluster if needed:

```bash
docker build -t todo-app:1.6 .
k3d image import todo-app:1.6 --cluster k3s-default
```

Create the Deployment and ClusterIP Service, then wait for the Pod:

```bash
kubectl apply -f manifests/
kubectl rollout status deployment/todo-app
```

Confirm that the configured port was used:

```bash
kubectl logs deployment/todo-app
```

The project's Ingress from exercise 1.8 is removed in exercise 1.9 while routing
is introduced for Log output and ping-pong. The application remains available
inside the cluster through `todo-app-svc` and directly through port forwarding.

For debugging, local port `3003` can still be forwarded directly to the
Deployment:

```bash
kubectl port-forward deployment/todo-app 3003:3000
```

Open <http://localhost:3003> in a browser. Stop port forwarding with `Ctrl+C`.
Port forwarding is intended only for local development and debugging.

Remove the Deployment and Service when they are no longer needed:

```bash
kubectl delete -f manifests/
```

If the cluster has a different name, replace `k3s-default` in the import
command. You can list cluster names with `k3d cluster list`.
