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

The commands below assume that Docker, kubectl, and k3d are available. Create a
cluster with host port `8081` mapped to the load balancer for Ingress access:

```bash
k3d cluster create \
  --port 8081:80@loadbalancer \
  --agents 2
```

The application code has not changed since exercise 1.6, so its existing image
tag can be reused. Build the image and import it into the cluster if needed:

```bash
docker build -t todo-app:1.6 .
k3d image import todo-app:1.6 --cluster k3s-default
```

Create the Deployment, ClusterIP Service, and Ingress, then wait for the Pod:

```bash
kubectl apply -f manifests/
kubectl rollout status deployment/todo-app
```

Confirm that the configured port was used:

```bash
kubectl logs deployment/todo-app
```

Open <http://localhost:8081> in a browser. The request travels through the k3d
host-port mapping to Traefik and the Ingress, then through the ClusterIP Service
to container port `3000`.

For debugging, local port `3003` can still be forwarded directly to the
Deployment:

```bash
kubectl port-forward deployment/todo-app 3003:3000
```

Open <http://localhost:3003> in a browser. Stop port forwarding with `Ctrl+C`.
Port forwarding is intended only for local development and debugging.

Remove the Deployment, Service, and Ingress when they are no longer needed:

```bash
kubectl delete -f manifests/
```

If the cluster has a different name, replace `k3s-default` in the import
command. You can list cluster names with `k3d cluster list`.
