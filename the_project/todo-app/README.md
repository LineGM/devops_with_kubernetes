# Todo app

The course Todo App serves an HTML page and a random image from Lorem Picsum.
The image is downloaded on demand and cached in a PersistentVolume for ten
minutes. Because the cache is stored outside the container, a Pod restart does
not cause another download while the image is still fresh.

If refreshing an expired image fails, the server continues serving the stale
cached image. Concurrent requests are protected by a process-local lock, and a
new download atomically replaces the old file.

## Run locally

Python 3.11 or newer is recommended. The application has no third-party
dependencies.

```bash
mkdir -p files
IMAGE_CACHE_FILE="$PWD/files/image.jpg" PORT=8080 python3 app/main.py
```

Open <http://localhost:8080> and stop the server with `Ctrl+C`.

The cache lifetime defaults to 600 seconds and can be configured with
`IMAGE_CACHE_MAX_AGE_SECONDS`.

## Deploy to a local k3d cluster

Run the commands from the repository root. They assume a k3d cluster named
`k3s-default` whose host port `8081` is mapped to port `80` of its load balancer.

Build the image and import it into the cluster:

```bash
docker build -t todo-app:1.12 ./the_project/todo-app
k3d image import todo-app:1.12 --cluster k3s-default
```

Create the local backing directory, storage resources, Deployment, Service, and
Ingress:

```bash
docker exec k3d-k3s-default-agent-0 mkdir -p /tmp/todo-image
kubectl apply -f the_project/manifests/persistentvolume.yaml
kubectl apply -f the_project/manifests/persistentvolumeclaim.yaml
kubectl apply -f the_project/todo-app/manifests/
kubectl delete ingress log-output-ingress --ignore-not-found
kubectl apply -f the_project/manifests/ingress.yaml
kubectl rollout status deployment/todo-app
```

The old Log output Ingress is removed because both it and the project use the
same catch-all `/` path. Open <http://localhost:8081> to view the application.

Verify that the claim is bound and inspect application logs with:

```bash
kubectl get pv todo-image-pv
kubectl get pvc todo-image-claim
kubectl logs deployment/todo-app
```

To verify persistence, request `/image`, recreate the Pod, and request the image
again. Its checksum should remain unchanged while the cached file is younger
than ten minutes:

```bash
curl --output /tmp/image-before.jpg http://localhost:8081/image
kubectl delete pod -l app=todo-app
kubectl wait --for=condition=Ready pod -l app=todo-app --timeout=120s
curl --output /tmp/image-after.jpg http://localhost:8081/image
sha256sum /tmp/image-before.jpg /tmp/image-after.jpg
```
