# Course project

The course project currently consists of the Todo App web server and its
Kubernetes resources. The application displays a random Lorem Picsum image and
caches it for ten minutes in a PersistentVolume. Its interface includes an
input limited to 140 characters, a send button, and a hardcoded todo list.

Application code, its Deployment, Service, and detailed instructions are in
[`todo-app`](todo-app/). Cluster-level storage and Ingress resources are in
[`manifests`](manifests/).
