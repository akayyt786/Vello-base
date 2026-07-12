# variables.tf — inputs for the OwnFirebase Helm deployment module.
#
# Kept deliberately minimal: only things that actually vary per-deploy are
# exposed here. Anything the chart already defaults sensibly (e.g. whether to
# run postgres/redis/minio in-cluster, resource requests/limits, service
# ports) is left alone — override it directly in
# deploy/helm/ownfirebase/values.yaml or with an extra `values.tfvars`-driven
# `values = [...]` entry in main.tf if you need it later.

variable "kube_context" {
  description = <<-EOT
    kubeconfig context to deploy into. Defaults to the context name `kind`
    generates for a cluster created with `kind create cluster --name
    ownfirebase` (kind always names the context "kind-<cluster-name>").

    For a real cloud cluster, merge its kubeconfig locally and point this at
    that context instead — e.g.:
      aws eks update-kubeconfig --name my-cluster --alias my-eks
      gcloud container clusters get-credentials my-cluster --zone us-central1-a
      az aks get-credentials --name my-cluster --resource-group my-rg
    then set kube_context = "my-eks" (or whatever --alias/context name was
    produced). No other file in this module needs to change.
  EOT
  type        = string
  default     = "kind-ownfirebase"
}

variable "kubeconfig_path" {
  description = "Path to the kubeconfig file both providers read. Defaults to the standard local kubeconfig; override only if yours lives somewhere non-standard."
  type        = string
  default     = "~/.kube/config"
}

variable "namespace" {
  description = "Kubernetes namespace the release, its Secret, and all chart-managed resources are created in. Created by this module (kubernetes_namespace_v1.ownfirebase) — it does not need to exist beforehand."
  type        = string
  default     = "ownfirebase"
}

variable "django_secret_key" {
  description = <<-EOT
    Django SECRET_KEY. Required, intentionally has no default — ownfirebase/settings.py
    does `SECRET_KEY = os.environ['DJANGO_SECRET_KEY']` and refuses to start
    without it. Generate one with:
      python -c "import secrets; print(secrets.token_urlsafe(50))"
    Supply via a git-ignored terraform.tfvars, TF_VAR_django_secret_key, or a
    secrets manager wired into your CI — never commit it.
  EOT
  type        = string
  sensitive   = true
}

variable "database_password" {
  description = "Password for the Postgres role the app connects with (DATABASE_PASSWORD). Required, no default — generate a strong random value per environment."
  type        = string
  sensitive   = true
}

variable "sentry_dsn" {
  description = "Optional Sentry DSN (core/observability.py: init_sentry() reads SENTRY_DSN and is a no-op when it's unset). Leave empty (the default) to keep error tracking disabled, which is normal for a local kind deployment."
  type        = string
  sensitive   = true
  default     = ""
}

variable "extra_secret_env" {
  description = <<-EOT
    Additional sensitive values that don't have a first-class variable of
    their own yet. Keys MUST match a field name under
    deploy/helm/ownfirebase/values.yaml's `secrets:` block (camelCase —
    e.g. stripeSecretKey, stripeWebhookSecret, twilioAuthToken,
    fcmServerKey, vapidPrivateKey, githubClientSecret, aiProviderKek), NOT
    the app's SCREAMING_SNAKE_CASE env var names — each key is passed to
    Helm as `secrets.<key>` (see main.tf's set_sensitive block) as well as
    merged into the standalone kubernetes_secret_v1 alongside
    django_secret_key/database_password/sentry_dsn. A key that doesn't
    match a real `secrets.*` field is a silent no-op through Helm (it still
    lands in the standalone Secret object, just isn't wired into any pod's
    env) — see terraform.tfvars.example for the exact supported keys.

    Nothing in this codebase currently reads a single global STRIPE_* env
    var (billing/ stores per-project Stripe credentials in the database
    instead — see billing/models.py); the chart's secrets.stripeSecretKey/
    secrets.stripeWebhookSecret fields exist for forward-compatibility with
    a future app change, not current billing/ usage.
  EOT
  type        = map(string)
  sensitive   = true
  default     = {}
}

variable "image_tag" {
  description = "Image tag deployed for the Django app (web/websocket/celery-worker/celery-beat all share the Dockerfile built image per docker-compose.yml). Defaults to 'latest' for local kind iteration; pin an explicit tag for anything beyond throwaway testing. Does NOT affect the separate Rust push-worker image, which the chart tags independently."
  type        = string
  default     = "latest"
}

variable "replica_counts" {
  description = <<-EOT
    Replica counts per component, mapped to the chart's per-component
    replicaCount values. Any field left unset defaults to 1.

    celery_beat is NOT currently wired to the chart — deployment-celery-beat.yaml
    hardcodes `replicas: 1` server-side and reads no values field (Celery
    Beat is not safe to run more than one of: every periodic task would
    fire once per running beat replica). This field and its validation are
    kept for documentation/forward-compatibility only; setting it has no
    effect through Helm today.
  EOT
  type = object({
    web           = optional(number, 1)
    websocket     = optional(number, 1)
    celery_worker = optional(number, 1)
    celery_beat   = optional(number, 1)
  })
  default = {}

  validation {
    condition     = var.replica_counts.celery_beat <= 1
    error_message = "replica_counts.celery_beat must be 0 or 1 — running more than one Celery Beat process double-schedules every periodic task."
  }
}

variable "enable_websocket" {
  description = <<-EOT
    NOT currently wired to the chart: deploy/helm/ownfirebase has no
    websocket.enabled toggle — the websocket (Daphne/ASGI, realtime/ app)
    Deployment is unconditional by design (that split is the actual fix for
    the docker-compose.prod.yml WebSocket gap, so making it optional would
    undercut the point). Kept as a variable for forward-compatibility if
    the chart ever grows that toggle; setting it has no effect today.
  EOT
  type        = bool
  default     = true
}

variable "enable_push_worker" {
  description = <<-EOT
    Deploy the Rust push-worker Deployment (rust/push-worker) that delivers
    FCM/APNs/web-push notifications.

    Defaults to false, matching the chart's own conservative default
    (deploy/helm/ownfirebase/values.yaml: pushWorker.enabled: false) —
    confirmed live: defaulting this to true here (its original value)
    against a cluster where `ownfirebase/push-worker:latest` was never
    built left the pod stuck in ImagePullBackOff indefinitely, which in
    turn made `helm_release`'s default `wait = true` block for the full
    300s timeout and fail the apply. Only enable this after building and
    loading/pushing that image yourself — see values.yaml's comment on
    `pushWorker` for the exact (non-obvious) build command.
  EOT
  type        = bool
  default     = false
}
