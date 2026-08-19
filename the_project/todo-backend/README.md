# Todo backend

Todo backend is an in-memory JSON API for the course project.

- `GET /todos` returns the current todo list.
- `POST /todos` accepts `{ "content": "..." }` and creates a todo.
- Todo content must contain between 1 and 140 characters after trimming.

The data resets whenever the process restarts. Persistent database storage will
be added in a later exercise.

The server has no deployment-specific defaults. Its listening address, port,
API path, todo length, and request size limit are supplied through environment
variables from `todo-project-config` in Kubernetes.

## Run locally

```bash
HOST=127.0.0.1 \
PORT=3001 \
TODOS_PATH=/todos \
MAX_TODO_LENGTH=140 \
MAX_REQUEST_BYTES=4096 \
python3 app/main.py
curl http://localhost:3001/todos
curl --json '{"content":"Learn Services"}' http://localhost:3001/todos
```

## Deploy to k3d

Run the commands from the repository root:

```bash
docker build -t todo-backend:2.6 ./the_project/todo-backend
k3d image import todo-backend:2.6 --cluster k3s-default
kubectl apply -f namespaces/project.yaml
kubectl apply -f the_project/manifests/configmap.yaml
kubectl apply -f the_project/todo-backend/manifests/
kubectl rollout status deployment/todo-backend -n project
```

The project Ingress routes `/todos` to `todo-backend-svc` inside the `project`
namespace.
