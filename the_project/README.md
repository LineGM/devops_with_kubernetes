# Course project

The course project currently consists of the Todo App web server and its
Kubernetes resources. The application displays a random Lorem Picsum image and
caches it for ten minutes in a PersistentVolume.

Application code, its Deployment, Service, and detailed instructions are in
[`todo-app`](todo-app/). Cluster-level storage and Ingress resources are in
[`manifests`](manifests/).
