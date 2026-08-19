# Local persistent storage

These cluster-level manifests provide a local PersistentVolume and a matching
PersistentVolumeClaim shared by Log output and ping-pong. Local volumes are
suitable for this k3d exercise, but they tie data to one node and are not a
production storage solution.

Create the backing directory inside the node selected by the PV's node
affinity, then apply the storage manifests:

```bash
docker exec k3d-k3s-default-agent-0 mkdir -p /tmp/kube
kubectl apply -f storage/
kubectl get pv,pvc
```

Both resources should reach the `Bound` phase before the application
Deployments are applied.
