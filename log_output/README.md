# Log output

Log output runs as two containers in one Pod. The writer generates a UUID once
at startup and stores that value with a fresh UTC timestamp in a shared file
every five seconds. The reader combines this status with the persistent
ping-pong request count and serves both over HTTP. A PersistentVolumeClaim makes
the files visible to both applications and preserves them across Pod restarts.

## Run locally

Python 3.11 or newer is recommended. The applications have no third-party
dependencies. Start the writer and reader in separate terminals with the same
file path:

```bash
mkdir -p files
LOG_FILE="$PWD/files/log.txt" python3 writer/main.py
```

```bash
LOG_FILE="$PWD/files/log.txt" \
COUNTER_FILE="$PWD/files/ping-pong.txt" \
PORT=3000 python3 reader/main.py
```

Open <http://localhost:3000> and stop both processes with `Ctrl+C`.

## Deploy to a local k3d cluster

The commands below assume that Docker, kubectl, k3d, and a running k3d cluster
named `k3s-default` are available.

Build both images and import them into the cluster:

```bash
docker build -f Dockerfile.writer -t log-output-writer:1.11 .
docker build -f Dockerfile.reader -t log-output-reader:1.11 .
k3d image import \
  log-output-writer:1.11 \
  log-output-reader:1.11 \
  --cluster k3s-default
```

Create the backing node directory and storage resources before applying the
application manifests:

```bash
docker exec k3d-k3s-default-agent-0 mkdir -p /tmp/kube
kubectl apply -f ../storage/
kubectl apply -f manifests/
kubectl rollout status deployment/log-output
```

Confirm that the application is running:

```bash
kubectl logs -f deployment/log-output -c log-writer
kubectl logs -f deployment/log-output -c log-reader
```

The HTTP output includes the latest writer status and persisted ping-pong count:

```text
2020-03-30T12:15:17.705Z: 8523ecb1-c716-4cb6-a044-b9e83bb98e43.
Ping / Pongs: 3
```

With host port `8081` mapped to the k3d load balancer's port `80`, open
<http://localhost:8081> to request Log output status. The same Ingress routes
<http://localhost:8081/pingpong> to the ping-pong application.

Remove all application resources when they are no longer needed:

```bash
kubectl delete -f manifests/
```

If the cluster has a different name, replace `k3s-default` in the import
command. You can list cluster names with `k3d cluster list`.
