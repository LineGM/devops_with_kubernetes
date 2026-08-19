# Todo app

Todo App serves the course project's HTML and JavaScript frontend. The browser
loads todos from `GET /todos` and submits new items to `POST /todos`; Ingress
routes those requests to the separate Todo backend service. The input and the
backend both enforce a maximum length of 140 characters.

The application also downloads a random image from Lorem Picsum and caches it
in a PersistentVolume for ten minutes. A Pod restart therefore does not trigger
another download while the image is still fresh.

## Run locally

Python 3.11 or newer is recommended. Start the backend and frontend in separate
terminals:

```bash
PORT=3001 python3 ../todo-backend/app/main.py
```

```bash
mkdir -p files
IMAGE_CACHE_FILE="$PWD/files/image.jpg" PORT=8080 python3 app/main.py
```

For a fully working local browser UI, use a reverse proxy that routes `/todos`
to port `3001`, or test the API directly. Kubernetes Ingress provides this
routing in the cluster.

## Deploy to a local k3d cluster

Run the commands from the repository root. They assume a k3d cluster named
`k3s-default` whose host port `8081` is mapped to port `80` of its load balancer.

Build and import both application images:

```bash
docker build -t todo-app:2.2 ./the_project/todo-app
docker build -t todo-backend:2.2 ./the_project/todo-backend
k3d image import todo-app:2.2 todo-backend:2.2 --cluster k3s-default
```

Create the image cache storage, deploy both services, and activate the project
Ingress:

```bash
docker exec k3d-k3s-default-agent-0 mkdir -p /tmp/todo-image
kubectl apply -f the_project/manifests/persistentvolume.yaml
kubectl apply -f the_project/manifests/persistentvolumeclaim.yaml
kubectl apply -f the_project/todo-app/manifests/
kubectl apply -f the_project/todo-backend/manifests/
kubectl delete ingress log-output-ingress --ignore-not-found
kubectl apply -f the_project/manifests/ingress.yaml
kubectl rollout status deployment/todo-app
kubectl rollout status deployment/todo-backend
```

Open <http://localhost:8081>. The form creates todos through the backend, and
the refreshed list is rendered without reloading the page.

The API can also be verified directly through Ingress:

```bash
curl http://localhost:8081/todos
curl --json '{"content":"Learn Kubernetes Services"}' \
  http://localhost:8081/todos
```
