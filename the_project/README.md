# Course project

The course project consists of two services. Todo App serves the browser UI and
caches a random Lorem Picsum image in a PersistentVolume. Todo backend provides
an in-memory JSON API for listing and creating todos. The browser reaches both
services through path-based Ingress routing.

Application code, Kubernetes manifests, and detailed instructions are in
[`todo-app`](todo-app/) and [`todo-backend`](todo-backend/). Cluster-level
storage and Ingress resources are in [`manifests`](manifests/).
