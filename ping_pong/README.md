# Ping-pong

Ping-pong stores its counter in PostgreSQL and exposes two HTTP endpoints:

- `GET /pingpong` responds with `pong N` and increments the counter.
- `GET /pings` responds with the current number without incrementing it.

The ClusterIP Service makes `/pings` available to Log output at
`http://ping-pong-svc/pings`. PostgreSQL runs as a one-replica StatefulSet with
a dynamically provisioned `local-path` volume, so the counter survives both
application and database Pod restarts.

Runtime settings come from `ping-pong-config`. The database password comes
from `ping-pong-postgres-secret`, which is deliberately not stored in Git.

## Run locally

Python 3.11 or newer and PostgreSQL are required. Install the Python dependency
and provide all runtime configuration:

```bash
python3 -m pip install -r requirements.txt
HOST=127.0.0.1 \
PORT=8080 \
PING_PONG_PATH=/pingpong \
PINGS_PATH=/pings \
DB_HOST=127.0.0.1 \
DB_PORT=5432 \
DB_NAME=pingpong \
DB_USER=pingpong \
DB_PASSWORD='<your-local-password>' \
DB_CONNECT_TIMEOUT_SECONDS=5 \
DB_CONNECT_RETRIES=30 \
DB_CONNECT_RETRY_DELAY_SECONDS=2 \
python3 app/main.py
curl http://localhost:8080/pingpong
curl http://localhost:8080/pings
```

Stop the server with `Ctrl+C`.

## Deploy to a local k3d cluster

Run these commands from the repository root:

```bash
docker build -t ping-pong:2.7 ./ping_pong
k3d image import ping-pong:2.7 --cluster k3s-default
kubectl apply -f namespaces/exercises.yaml
kubectl create secret generic ping-pong-postgres-secret \
  --namespace exercises \
  --from-literal=POSTGRES_PASSWORD='<choose-a-local-password>' \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f ping_pong/manifests/configmap.yaml
kubectl apply -f ping_pong/manifests/postgres.yaml
kubectl rollout status statefulset/ping-pong-postgres -n exercises
kubectl apply -f ping_pong/manifests/
kubectl rollout status deployment/ping-pong -n exercises
```

The Ingress stored with Log output routes `/pingpong` to this application and
`/` to Log output. The `/pings` endpoint is intended for internal communication
through `ping-pong-svc`.

Confirm persistence by incrementing the counter, restarting Ping-pong, and
reading the current value again:

```bash
curl http://localhost:8081/pingpong
kubectl rollout restart deployment/ping-pong -n exercises
kubectl rollout status deployment/ping-pong -n exercises
curl http://localhost:8081/pingpong
```

All Ping-pong resources are kept in the `exercises` namespace.
