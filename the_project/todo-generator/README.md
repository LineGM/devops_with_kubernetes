# Todo generator

Todo generator is a short-lived application run by a Kubernetes CronJob at the
start of every hour. It requests Wikipedia's random-page endpoint without
following the redirect, reads the article URL from the `Location` header, and
creates a `Read <URL>` item through the Todo backend API.

If a generated reminder exceeds the configured 140-character limit, the job
requests another article. Kubernetes prevents overlapping executions with
`concurrencyPolicy: Forbid` and retries failed Jobs up to three times.

## Run locally

Python 3.11 or newer is recommended. Start the Todo backend first, then run:

```bash
WIKIPEDIA_RANDOM_URL=https://en.wikipedia.org/wiki/Special:Random \
TODO_BACKEND_URL=http://localhost:3001/todos \
TODO_REMINDER_PREFIX="Read " \
MAX_TODO_LENGTH=140 \
HTTP_TIMEOUT_SECONDS=15 \
MAX_RANDOM_ATTEMPTS=10 \
python3 app/main.py
```

## Deploy to k3d

Run these commands from the repository root after the Todo backend is running:

```bash
docker build -t todo-generator:2.9 ./the_project/todo-generator
k3d image import todo-generator:2.9 --cluster k3s-default
kubectl apply -f the_project/manifests/configmap.yaml
kubectl apply -f the_project/todo-generator/manifests/cronjob.yaml
kubectl get cronjob -n project
```

The hourly schedule can be tested immediately by creating a one-off Job from
the CronJob template:

```bash
kubectl create job --from=cronjob/todo-generator \
  todo-generator-manual -n project
kubectl wait --for=condition=complete job/todo-generator-manual \
  -n project --timeout=120s
kubectl logs job/todo-generator-manual -n project
curl http://localhost:8081/todos
kubectl delete job todo-generator-manual -n project
```
