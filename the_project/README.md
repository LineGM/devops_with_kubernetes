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

Application code, Kubernetes manifests, and detailed instructions are in
[`todo-app`](todo-app/) and [`todo-backend`](todo-backend/). Cluster-level
storage and Ingress resources are in [`manifests`](manifests/).
