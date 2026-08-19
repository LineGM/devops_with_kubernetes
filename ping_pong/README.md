# Ping-pong

An HTTP server that responds to `GET /pingpong` with `pong N`, where `N` is an
in-memory counter. The first response is `pong 0`; each successful request
increments the counter. The value resets when the process restarts.

## Run locally

Python 3.11 or newer is recommended. The application has no third-party
dependencies.

```bash
PORT=8080 python3 app/main.py
curl http://localhost:8080/pingpong
```

Stop the server with `Ctrl+C`.

## Deploy to a local k3d cluster

Run these commands from the repository root. They assume that Docker, kubectl,
k3d, and a running cluster named `k3s-default` are available.

```bash
docker build -t ping-pong:1.9 ./ping_pong
k3d image import ping-pong:1.9 --cluster k3s-default
kubectl apply -f ping_pong/manifests/
kubectl apply -f log_output/manifests/
kubectl rollout status deployment/ping-pong
```

The Ingress stored with Log output routes `/pingpong` to this application's
Service and `/` to Log output. With host port `8081` mapped to the k3d load
balancer, test both routes:

```bash
curl http://localhost:8081/pingpong
curl http://localhost:8081/
```

Remove the ping-pong resources when they are no longer needed:

```bash
kubectl delete -f ping_pong/manifests/
```
