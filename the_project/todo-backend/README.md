# Todo backend

Todo backend is an in-memory JSON API for the course project.

- `GET /todos` returns the current todo list.
- `POST /todos` accepts `{ "content": "..." }` and creates a todo.
- Todo content must contain between 1 and 140 characters after trimming.

The data resets whenever the process restarts. Persistent database storage will
be added in a later exercise.

## Run locally

```bash
PORT=3001 python3 app/main.py
curl http://localhost:3001/todos
curl --json '{"content":"Learn Services"}' http://localhost:3001/todos
```

## Deploy to k3d

Run the commands from the repository root:

```bash
docker build -t todo-backend:2.2 ./the_project/todo-backend
k3d image import todo-backend:2.2 --cluster k3s-default
kubectl apply -f the_project/todo-backend/manifests/
kubectl rollout status deployment/todo-backend
```

The project Ingress routes `/todos` to `todo-backend-svc`.
