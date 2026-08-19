# Namespaces

The `exercises` namespace contains Log output, Ping-pong, and future
non-project exercises. The `project` namespace contains Todo App, Todo backend,
and all other namespaced project resources. Apply namespaces before application
manifests:

```bash
kubectl apply -f namespaces/exercises.yaml
kubectl apply -f namespaces/project.yaml
```
