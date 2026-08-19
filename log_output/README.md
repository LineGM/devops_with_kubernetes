# Log output

Log output runs as two containers in one Pod. The writer creates a UUID at
startup and stores it with a fresh UTC timestamp every five seconds. An
`emptyDir` shares that file only between the writer and reader containers.

For every `GET /`, the reader fetches the current counter from the separate
Ping-pong Pod through `http://ping-pong-svc/pings`. The stable Service name is
resolved by Kubernetes DNS; the two applications no longer share a volume.

## Run locally

Python 3.11 or newer is recommended. Start all three processes in separate
terminals:

```bash
PORT=3001 python3 ../ping_pong/app/main.py
```

```bash
mkdir -p files
LOG_FILE="$PWD/files/log.txt" python3 writer/main.py
```

```bash
LOG_FILE="$PWD/files/log.txt" \
PING_PONG_URL="http://localhost:3001/pings" \
PORT=3000 python3 reader/main.py
```

Open <http://localhost:3000> and stop the processes with `Ctrl+C`.

## Deploy to a local k3d cluster

Run these commands from the repository root. They assume that Docker, kubectl,
k3d, and a running cluster named `k3s-default` are available.

```bash
docker build -f log_output/Dockerfile.writer -t log-output-writer:2.1 ./log_output
docker build -f log_output/Dockerfile.reader -t log-output-reader:2.1 ./log_output
docker build -t ping-pong:2.1 ./ping_pong
k3d image import \
  log-output-writer:2.1 \
  log-output-reader:2.1 \
  ping-pong:2.1 \
  --cluster k3s-default
```

Apply both applications and switch the catch-all Ingress from the course
project back to Log output:

```bash
kubectl apply -f namespaces/exercises.yaml
kubectl apply -f ping_pong/manifests/
kubectl apply -f log_output/manifests/
kubectl delete ingress todo-app-ingress -n default --ignore-not-found
kubectl apply -f log_output/manifests/ingress.yaml
kubectl rollout status deployment/ping-pong -n exercises
kubectl rollout status deployment/log-output -n exercises
```

Test the public endpoints through the shared Ingress:

```bash
curl http://localhost:8081/pingpong
curl http://localhost:8081/
```

The Log output response contains data received from both Pods:

```text
2026-05-18T12:15:17.705Z: 8523ecb1-c716-4cb6-a044-b9e83bb98e43.
Ping / Pongs: 3
```

The internal endpoint can be tested from the reader container using the
Service's DNS name:

```bash
kubectl exec deployment/log-output -n exercises -c log-reader -- \
  python -c "from urllib.request import urlopen; print(urlopen('http://ping-pong-svc/pings').read().decode())"
```
