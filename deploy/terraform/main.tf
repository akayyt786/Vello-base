# main.tf — creates the namespace, a Secret holding the genuinely sensitive
# values, and the Helm release itself.
#
# Reconciled against the real deploy/helm/ownfirebase/values.yaml (this
# module was originally written in parallel, before the chart existed, on
# best-guess value paths). Three guessed secret paths were confirmed wrong
# and fixed below:
#   django.secretKey  -> secrets.djangoSecretKey
#   database.password -> secrets.databasePassword
#   sentry.dsn        -> secrets.sentryDsn
# All three would have left the chart's `required` guard on
# secrets.djangoSecretKey unsatisfied, failing `helm install` outright.
#
# Two guessed paths turned out to be no-ops against the real chart (Helm
# silently ignores a `--set` path with no matching template reference — no
# error, it just does nothing) and were removed rather than left silently
# broken:
#   websocket.enabled       — no such toggle exists; the websocket
#                             (daphne/ASGI) Deployment is unconditional by
#                             design (that split is the fix for the
#                             docker-compose.prod.yml WebSocket gap).
#   celeryBeat.replicaCount — deployment-celery-beat.yaml hardcodes
#                             `replicas: 1` and never reads a values field
#                             (Celery Beat is not safe to run >1 of).
# See variables.tf for the corresponding doc updates.

resource "kubernetes_namespace_v1" "ownfirebase" {
  metadata {
    name = var.namespace

    labels = {
      "app.kubernetes.io/part-of"    = "ownfirebase"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
}

# Holds every genuinely sensitive value (DB password, Django secret key,
# optional Sentry DSN, and any extra provider keys) as a real namespaced
# Secret object — never as plaintext in a .tfvars file that could get
# committed. This is independent of what Helm does with the same values
# below: it exists so kubectl/other tooling can read the values without
# going through Helm.
#
# Named "-terraform-secrets" rather than "-secrets" specifically to NOT
# collide with the Helm chart's own auto-created "<fullname>-secrets"
# Secret (deploy/helm/ownfirebase/templates/secret.yaml) — since
# helm_release.name == var.namespace here, "<fullname>" and "${var.namespace}"
# resolve to the exact same string, so a shared "-secrets" suffix on both
# sides names the identical object. Confirmed live: a real `terraform apply`
# against a kind cluster failed with "Secret ... exists and cannot be
# imported into the current release" because this resource created it
# first, then Helm's own install tried to create a Secret of the same name
# and refused since it lacked Helm's ownership labels/annotations. The chart
# has no `existingSecret` pattern today (no `.Values.existingSecret`
# conditional in secret.yaml), so this object is a read-only convenience
# copy, not something the Helm release actually consumes.
resource "kubernetes_secret_v1" "ownfirebase" {
  metadata {
    name      = "${var.namespace}-terraform-secrets"
    namespace = kubernetes_namespace_v1.ownfirebase.metadata[0].name
  }

  type = "Opaque"

  data = merge(
    {
      DJANGO_SECRET_KEY = var.django_secret_key
      DATABASE_PASSWORD = var.database_password
    },
    var.sentry_dsn != "" ? { SENTRY_DSN = var.sentry_dsn } : {},
    var.extra_secret_env,
  )
}

resource "helm_release" "ownfirebase" {
  name      = var.namespace
  namespace = kubernetes_namespace_v1.ownfirebase.metadata[0].name
  chart     = "../helm/ownfirebase"

  # The namespace is managed by kubernetes_namespace_v1.ownfirebase above, not
  # by Helm — avoid the two fighting over ownership of the same object.
  create_namespace = false

  # --- non-sensitive values --------------------------------------------------
  # enable_websocket / replica_counts.celery_beat have no corresponding
  # `set` entry: the chart always deploys the websocket Deployment (no
  # toggle exists), and celery-beat's replica count is hardcoded to 1 in
  # the template (no values field to set). See the file-header comment.
  set = [
    { name = "image.tag", value = var.image_tag },
    { name = "web.replicaCount", value = tostring(var.replica_counts.web) },
    { name = "websocket.replicaCount", value = tostring(var.replica_counts.websocket) },
    { name = "celeryWorker.replicaCount", value = tostring(var.replica_counts.celery_worker) },
    { name = "pushWorker.enabled", value = tostring(var.enable_push_worker) },
  ]

  # --- sensitive values -------------------------------------------------------
  # set_sensitive keeps these out of Terraform's plan/apply CLI output and
  # logs. It does NOT keep them out of the state file — Terraform state is
  # never secret-safe by itself, so treat terraform.tfstate as sensitive
  # (ideally via a remote backend with encryption at rest, e.g. an
  # encrypted S3 bucket + DynamoDB lock table, or Terraform Cloud) rather
  # than relying on set_sensitive alone.
  #
  # If deploy/helm/ownfirebase supports a chart convention of pointing at an
  # *existing* Secret instead of taking raw values (common in Helm charts,
  # e.g. `existingSecret: <name>`), prefer that over passing raw secret
  # material through Helm at all — swap the three entries below for one:
  #   { name = "existingSecret", value = kubernetes_secret_v1.ownfirebase.metadata[0].name }
  #
  # extra_secret_env keys are passed through verbatim as `secrets.<key>` —
  # they must match one of deploy/helm/ownfirebase/values.yaml's `secrets:`
  # field names (camelCase, e.g. stripeSecretKey, twilioAuthToken,
  # fcmServerKey, vapidPrivateKey, githubClientSecret, aiProviderKek), NOT
  # the app's SCREAMING_SNAKE_CASE env var names — see terraform.tfvars.example.
  set_sensitive = concat(
    [
      { name = "secrets.djangoSecretKey", value = var.django_secret_key },
      { name = "secrets.databasePassword", value = var.database_password },
    ],
    var.sentry_dsn != "" ? [{ name = "secrets.sentryDsn", value = var.sentry_dsn }] : [],
    [
      for k, v in var.extra_secret_env : { name = "secrets.${k}", value = v }
    ],
  )

  depends_on = [
    kubernetes_namespace_v1.ownfirebase,
    kubernetes_secret_v1.ownfirebase,
  ]
}
