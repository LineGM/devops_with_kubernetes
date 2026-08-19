# Course project

The course project consists of two services. Todo App serves the browser UI and
caches a random Lorem Picsum image in a PersistentVolume. Todo backend provides
a PostgreSQL-backed JSON API for listing and creating todos. The browser reaches
both services through path-based Ingress routing. All namespaced resources
belonging to the course project are kept in the `project` namespace. The image
cache uses a manually provisioned PersistentVolume, while the database
StatefulSet gets its own dynamically provisioned `local-path` volume.

Runtime configuration is stored in the `todo-project-config` ConfigMap and
injected into both Pods as environment variables. Application source contains
no deployment-specific ports, URLs, paths, cache settings, or request limits.
The database password is read from `todo-postgres-secret` and is never stored in
the repository.

The Todo generator runs as an hourly CronJob. It follows the redirect from
Wikipedia's random article endpoint and creates a `Read <URL>` item through the
internal Todo backend Service.

Todo backend writes a structured `todo_submission` JSON event for every parsed
creation request, including rejected items. These stdout events are collected
by the cluster logging stack and can be filtered in Loki through Grafana.

Application code, Kubernetes manifests, and detailed instructions are in
[`todo-app`](todo-app/), [`todo-backend`](todo-backend/), and
[`todo-generator`](todo-generator/). Cluster-level storage, configuration, and
Ingress resources are in [`manifests`](manifests/).
