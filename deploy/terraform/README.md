# OwnFirebase — Terraform module (Helm deploy)

Deploys the `deploy/helm/ownfirebase` chart to a Kubernetes cluster using
Terraform's `helm` and `kubernetes` providers. Written and tested against a
local **kind** cluster — no cloud provider resources are defined here (no
`aws_eks_cluster`, no GKE/AKS resources). A real cloud target is a described
extension (below), not something this module provisions itself.

## What this module creates

- `kubernetes_namespace_v1.ownfirebase` — the namespace the release lives in.
- `kubernetes_secret_v1.ownfirebase` — a namespaced Secret holding the
  genuinely sensitive values (`DJANGO_SECRET_KEY`, `DATABASE_PASSWORD`,
  optional `SENTRY_DSN`, anything in `extra_secret_env`). These same values
  are also passed into the Helm release via `set_sensitive` (see the note in
  `main.tf`) — nothing sensitive is ever written to a `.tfvars` file that's
  meant to be committed.
- `helm_release.ownfirebase` — installs `../helm/ownfirebase` by local chart
  path (relative to this directory: `deploy/terraform/../helm/ownfirebase` =
  `deploy/helm/ownfirebase`).

## Prerequisites

1. **Terraform** (this module was written and `terraform validate`-checked
   against Terraform v1.15.8 — see "Verification" below). Install via:
   ```
   brew tap hashicorp/tap
   brew install hashicorp/tap/terraform
   ```
2. **A local `kind` cluster** named to match `kube_context`'s default
   (`kind-ownfirebase`, i.e. a cluster literally named `ownfirebase`):
   ```
   kind create cluster --name ownfirebase
   ```
   `kind` merges a context named `kind-ownfirebase` into `~/.kube/config`
   automatically — that's why the module's default `kube_context` is
   `"kind-ownfirebase"`. If your cluster has a different name, set
   `kube_context` to match (`kind-<your-cluster-name>`).
3. **The `deploy/helm/ownfirebase` chart** must exist (it's authored
   separately/in parallel — see the assumption note below).
4. `kubectl` for port-forwarding / poking at the cluster afterwards.

## Running it

```
cd deploy/terraform
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars: real django_secret_key, database_password, etc.

terraform init
terraform plan
terraform apply
```

`terraform init` downloads the `helm` (~> 3.0) and `kubernetes` (~> 3.0)
providers; both were pinned to major version 3 deliberately (see
`providers.tf` — the 3.x generation of both providers has a different HCL
schema than the older 2.x generation people may remember, e.g.
`helm_release`'s `set`/`set_sensitive` are list-of-object attributes now,
not repeated blocks).

To tear it down: `terraform destroy`.

## Reaching the app from your host machine

**kind does not provision a real cloud LoadBalancer.** If the chart creates a
`Service` of type `LoadBalancer` or an `Ingress` fronted by one, its
`EXTERNAL-IP` will sit at `<pending>` forever on kind — that is expected, not
a bug. Two real options:

### Option A — `kubectl port-forward` (default, always works)

```
terraform output port_forward_command
# kubectl --context kind-ownfirebase -n ownfirebase port-forward svc/ownfirebase-web 8080:8000
```

Run the printed command, then open `http://localhost:8080`. If the chart's
Helm fullname template doesn't happen to produce a Service literally named
`<namespace>-web`, check the real name with:
```
kubectl --context kind-ownfirebase -n ownfirebase get svc
```
and adjust the command's `svc/...` target accordingly.

### Option B — Ingress via kind's `extraPortMappings` (optional)

If you want to exercise the real Ingress path (nginx-ingress + host-based
routing) rather than bypass it with port-forward, create the kind cluster
with host ports 80/443 mapped in, then install ingress-nginx's kind-specific
manifest:

```yaml
# kind-config.yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: ownfirebase
nodes:
  - role: control-plane
    kubeadmConfigPatches:
      - |
        kind: InitConfiguration
        nodeRegistration:
          kubeletExtraArgs:
            node-labels: "ingress-ready=true"
    extraPortMappings:
      - containerPort: 80
        hostPort: 80
        protocol: TCP
      - containerPort: 443
        hostPort: 443
        protocol: TCP
```
```
kind create cluster --name ownfirebase --config kind-config.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
```
Then, after `terraform apply`, find the Ingress host and add it to
`/etc/hosts` pointing at `127.0.0.1`:
```
kubectl --context kind-ownfirebase -n ownfirebase get ingress
```
Without both `extraPortMappings` *and* ingress-nginx installed, an Ingress
object alone is not reachable from your host on kind — fall back to Option A.

## Cloud extension (not implemented here, by design)

This module intentionally has zero cloud-provider resources — there's no way
to test `aws_eks_cluster`/GKE/AKS resources against a `kind`-only sandbox
without them being unverified guesswork. To point this same module at a real
managed cluster instead:

1. Provision the cluster however you like (a separate Terraform
   root/module using `aws_eks_cluster`, `google_container_cluster`,
   `azurerm_kubernetes_cluster`, or click-ops — this module doesn't care).
2. Merge that cluster's kubeconfig locally, e.g.:
   ```
   aws eks update-kubeconfig --name my-cluster --alias my-eks
   gcloud container clusters get-credentials my-cluster --zone us-central1-a
   az aks get-credentials --name my-cluster --resource-group my-rg
   ```
3. Set `kube_context` to whatever context name that produced (check with
   `kubectl config get-contexts`).
4. Run `terraform init && terraform plan && terraform apply` from this same
   directory, unchanged. Nothing else needs editing.

For a real production rollout you'd also want: a remote encrypted Terraform
state backend (this module has none configured — it uses local state, which
is fine for kind but not for a shared cloud environment), TLS on the Ingress
(cert-manager + a real DNS name instead of `/etc/hosts`), and pulling
`django_secret_key`/`database_password`/etc. from a real secrets manager
(AWS Secrets Manager, GCP Secret Manager, Vault) instead of a
`terraform.tfvars` file.

## Verification performed in this environment

- `terraform init` and `terraform validate` **were** runnable here (Terraform
  CLI was not preinstalled; it was installed via
  `brew install hashicorp/tap/terraform`, which succeeded — network access
  was available). Both passed cleanly against the real files in this
  directory using the real `helm` and `kubernetes` provider schemas (not
  guessed from memory — see judgment calls below).
- `terraform plan` / `terraform apply` were **not** run: no cluster exists in
  this sandbox, and the task explicitly reserves `apply` for you to run
  against your real `kind` cluster.
- **Update (post-reconciliation): `deploy/helm/ownfirebase` now exists** and
  every `set`/`set_sensitive` path in `main.tf` has been diffed against its
  real `values.yaml` by hand (`helm show values ../helm/ownfirebase`). Three
  guessed secret paths were wrong and are now fixed (`django.secretKey` ->
  `secrets.djangoSecretKey`, `database.password` -> `secrets.databasePassword`,
  `sentry.dsn` -> `secrets.sentryDsn`); two guessed paths were no-ops against
  the real chart and were removed (`websocket.enabled` — no such toggle,
  the chart always deploys it; `celeryBeat.replicaCount` — hardcoded to 1 in
  the template). See the updated header comment in `main.tf` for the full
  list. The original "guessed, not verified" caveat below is kept for
  context but no longer describes the current state of this file.

## Judgment calls / things worth double-checking

- **Provider major version**: `terraform init` in this sandbox resolved
  `helm` to 3.2.0 and `kubernetes` to 3.2.1 (latest at time of writing).
  Both had breaking schema changes at v3 vs the v2.x generation — this
  module is written for and pinned (`~> 3.0`) to the v3 schema. If your own
  `terraform init` somehow resolves an older major version, either upgrade
  or you'll need to rewrite `main.tf`'s `set`/`set_sensitive` blocks back to
  the repeated-block syntax.
- **`kubernetes_namespace_v1` / `kubernetes_secret_v1`** were used instead of
  the plain `kubernetes_namespace` / `kubernetes_secret` resource types —
  the provider marks the latter as deprecated (in favor of the `_v1` names)
  as of the version resolved here.
- **Helm value paths are guessed**, not verified (see above) — `image.tag`,
  `web.replicaCount`, `websocket.enabled`/`replicaCount`,
  `celeryWorker.replicaCount`, `celeryBeat.replicaCount`,
  `pushWorker.enabled`, `django.secretKey`, `database.password`,
  `sentry.dsn`, `extraSecretEnv.<key>`. Helm silently ignores a `--set` path
  that doesn't exist in a chart rather than erroring, so a mismatch here
  will not surface as a Terraform error — it needs a manual diff against the
  real `values.yaml`.
- **`existingSecret` pattern**: if the real chart supports pointing at an
  existing Secret by name (a common Helm convention) rather than taking raw
  secret values through `--set`, prefer that — it avoids passing secret
  material through Helm's own value-templating path a second time. The
  `kubernetes_secret_v1.ownfirebase` resource already exists for this; see
  the comment in `main.tf` for the one-line swap.
- **`image_tag` applies to the Django image only** (web/websocket/celery
  share one Dockerfile-built image per `docker-compose.yml`), not to the
  separate Rust `push-worker` image (`rust/push-worker/Dockerfile`) — the
  chart's default push-worker tag is left alone since the task only asked
  for one `image_tag` knob.
- **No `STRIPE_*` Terraform variable**: this codebase doesn't read a global
  Stripe env var — `billing/models.py` stores `stripe_customer_id` /
  `stripe_subscription_id` per-tenant in the database rather than a single
  API key from the environment. `extra_secret_env` covers this (and Twilio,
  FCM, VAPID, etc.) generically instead of inventing a variable name nothing
  in the app currently reads.
- **`celery_beat` replica count is capped at 1** by a `variables.tf`
  validation block — running more than one active Celery Beat process
  double-fires every scheduled task.
- **Local state, no remote backend**: fine for a disposable `kind` cluster;
  called out above as something to add before pointing this at anything
  shared/production.
