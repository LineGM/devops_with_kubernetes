# Ping-pong

Ping-pong stores its counter in memory and exposes two HTTP endpoints:

- `GET /pingpong` responds with `pong N` and increments the counter.
- `GET /pings` responds with the current number without incrementing it.

The ClusterIP Service makes `/pings` available to Log output at
`http://ping-pong-svc/pings`. No volume is shared between the applications in
exercise 2.1, so the counter may reset when the Ping-pong Pod restarts.

## Run locally

Python 3.11 or newer is recommended. The application has no third-party
dependencies.

```bash
PORT=8080 python3 app/main.py
curl http://localhost:8080/pingpong
curl http://localhost:8080/pings
```

Stop the server with `Ctrl+C`.

## Deploy to a local k3d cluster

Run these commands from the repository root:

```bash
docker build -t ping-pong:2.1 ./ping_pong
k3d image import ping-pong:2.1 --cluster k3s-default
kubectl apply -f namespaces/exercises.yaml
kubectl apply -f ping_pong/manifests/
kubectl rollout status deployment/ping-pong -n exercises
```

The Ingress stored with Log output routes `/pingpong` to this application and
`/` to Log output. The `/pings` endpoint is intended for internal communication
through `ping-pong-svc`.

All Ping-pong resources are kept in the `exercises` namespace.
