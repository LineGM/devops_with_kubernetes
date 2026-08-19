# Todo app

Todo App serves the course project's HTML and JavaScript frontend. The browser
loads todos from `GET /todos` and submits new items to `POST /todos`; Ingress
routes those requests to the separate Todo backend service. The input and the
backend both enforce a maximum length of 140 characters.

The application also downloads a random image from Lorem Picsum and caches it
in a PersistentVolume for ten minutes. A Pod restart therefore does not trigger
another download while the image is still fresh.

The application requires its runtime settings as environment variables. In
Kubernetes, `todo-project-config` supplies the listening address and port,
application/API paths, image source and cache settings, and request limits.

## Run locally

Python 3.11 or newer is recommended. Start the backend and frontend in separate
terminals:

```bash
HOST=127.0.0.1 \
PORT=3001 \
TODOS_PATH=/todos \
MAX_TODO_LENGTH=140 \
MAX_REQUEST_BYTES=4096 \
python3 ../todo-backend/app/main.py
```

```bash
mkdir -p files
HOST=127.0.0.1 \
PORT=8080 \
APP_PATH=/ \
IMAGE_PATH=/image \
TODO_API_URL=/todos \
IMAGE_URL=https://picsum.photos/1200 \
IMAGE_CACHE_FILE="$PWD/files/image.jpg" \
IMAGE_CACHE_MAX_AGE_SECONDS=600 \
IMAGE_MAX_BYTES=20971520 \
IMAGE_DOWNLOAD_TIMEOUT_SECONDS=30 \
MAX_TODO_LENGTH=140 \
python3 app/main.py
```

For a fully working local browser UI, use a reverse proxy that routes `/todos`
to port `3001`, or test the API directly. Kubernetes Ingress provides this
routing in the cluster.

## Deploy to a local k3d cluster

Run the commands from the repository root. They assume a k3d cluster named
`k3s-default` whose host port `8081` is mapped to port `80` of its load balancer.

Build and import both application images:

```bash
docker build -t todo-app:2.6 ./the_project/todo-app
docker build -t todo-backend:2.6 ./the_project/todo-backend
k3d image import todo-app:2.6 todo-backend:2.6 --cluster k3s-default
```

Create the image cache storage, deploy both services, and activate the project
Ingress:

When migrating an existing exercise 2.2 installation from `default`, first
remove the old namespaced resources and recreate the local PV object. Its
`Retain` policy leaves `/tmp/todo-image/image.jpg` intact:

```bash
kubectl delete deployment todo-app todo-backend -n default --ignore-not-found
kubectl delete service todo-app-svc todo-backend-svc -n default --ignore-not-found
kubectl delete ingress todo-app-ingress -n default --ignore-not-found
kubectl delete pvc todo-image-claim -n default --ignore-not-found
kubectl delete pv todo-image-pv --ignore-not-found
```

Then apply the namespace and current manifests:

```bash
kubectl apply -f namespaces/project.yaml
docker exec k3d-k3s-default-agent-0 mkdir -p /tmp/todo-image
kubectl apply -f the_project/manifests/persistentvolume.yaml
kubectl apply -f the_project/manifests/persistentvolumeclaim.yaml
kubectl apply -f the_project/manifests/configmap.yaml
kubectl apply -f the_project/todo-app/manifests/
kubectl apply -f the_project/todo-backend/manifests/
kubectl delete ingress log-output-ingress -n exercises --ignore-not-found
kubectl apply -f the_project/manifests/ingress.yaml
kubectl rollout status deployment/todo-app -n project
kubectl rollout status deployment/todo-backend -n project
```

Open <http://localhost:8081>. The form creates todos through the backend, and
the refreshed list is rendered without reloading the page.

The API can also be verified directly through Ingress:

```bash
curl http://localhost:8081/todos
curl --json '{"content":"Learn Kubernetes Services"}' \
  http://localhost:8081/todos
```
