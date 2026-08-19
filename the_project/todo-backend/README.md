# Todo backend

Todo backend is a PostgreSQL-backed JSON API for the course project.

- `GET /todos` returns the current todo list.
- `POST /todos` accepts `{ "content": "..." }` and creates a todo.
- Todo content must contain between 1 and 140 characters after trimming.

Every parsed submission is logged as a structured `todo_submission` JSON event.
The event contains the submitted content, its length, whether it was accepted,
and the rejection reason. This includes Todo items rejected for exceeding the
140-character backend limit.

PostgreSQL runs as a one-replica StatefulSet and stores its data in a dynamically
provisioned `local-path` volume. Todos therefore survive restarts of both the
backend Deployment and the database Pod.

The server has no deployment-specific defaults. Its listening address, port,
API path, todo length, request size limit, and database connection settings are
supplied through environment variables from `todo-project-config`. The database
password comes from `todo-postgres-secret` and is not committed to Git.

## Run locally

```bash
python3 -m pip install -r requirements.txt
HOST=127.0.0.1 \
PORT=3001 \
TODOS_PATH=/todos \
MAX_TODO_LENGTH=140 \
MAX_REQUEST_BYTES=4096 \
DB_HOST=127.0.0.1 \
DB_PORT=5432 \
DB_NAME=todos \
DB_USER=todo \
DB_PASSWORD='<your-local-password>' \
DB_CONNECT_TIMEOUT_SECONDS=5 \
DB_CONNECT_RETRIES=30 \
DB_CONNECT_RETRY_DELAY_SECONDS=2 \
python3 app/main.py
curl http://localhost:3001/todos
curl --json '{"content":"Learn Services"}' http://localhost:3001/todos
```

## Deploy to k3d

Run the commands from the repository root:

```bash
docker build -t todo-backend:2.10 ./the_project/todo-backend
k3d image import todo-backend:2.10 --cluster k3s-default
kubectl apply -f namespaces/project.yaml
kubectl create secret generic todo-postgres-secret \
  --namespace project \
  --from-literal=POSTGRES_PASSWORD='<choose-a-local-password>' \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f the_project/manifests/configmap.yaml
kubectl apply -f the_project/manifests/postgres.yaml
kubectl rollout status statefulset/todo-postgres -n project
kubectl apply -f the_project/todo-backend/manifests/
kubectl rollout status deployment/todo-backend -n project
```

The project Ingress routes `/todos` to `todo-backend-svc` inside the `project`
namespace.

To verify persistence, create a Todo, restart the backend or PostgreSQL
StatefulSet, and fetch the list again.

To verify request logging and backend validation, submit a value longer than
140 characters and inspect the log:

```bash
curl --json '{"content":"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}' \
  http://localhost:8081/todos
kubectl logs deployment/todo-backend -n project | grep todo_submission
```

With the course monitoring stack installed, the rejected event is available in
Grafana's Loki datasource with this LogQL query:

```logql
{namespace="project"} |= "todo_submission" |= "content_too_long"
```
