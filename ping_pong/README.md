# Ping-pong

An HTTP server that responds to `GET /pingpong` with `pong N`, where `N` is a
counter stored on a PersistentVolume shared with Log output. The first response
on an empty volume is `pong 0`; each successful request increments the persisted
value.

## Run locally

Python 3.11 or newer is recommended. The application has no third-party
dependencies.

```bash
mkdir -p files
COUNTER_FILE="$PWD/files/ping-pong.txt" PORT=8080 python3 app/main.py
curl http://localhost:8080/pingpong
```

Stop the server with `Ctrl+C`.

## Deploy to a local k3d cluster

Run these commands from the repository root. They assume that Docker, kubectl,
k3d, and a running cluster named `k3s-default` are available.

```bash
docker build -t ping-pong:1.11 ./ping_pong
k3d image import ping-pong:1.11 --cluster k3s-default
docker exec k3d-k3s-default-agent-0 mkdir -p /tmp/kube
kubectl apply -f storage/
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
