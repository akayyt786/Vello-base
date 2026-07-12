# outputs.tf
#
# There is deliberately no "url" or "ingress_ip" output here: kind clusters
# do not provision a real cloud LoadBalancer, so any Ingress/Service of type
# LoadBalancer created by the chart will show its EXTERNAL-IP stuck at
# <pending> forever on kind. Reaching the app from your host machine needs
# either `kubectl port-forward` (works everywhere, no kind config needed —
# the reliable default, see port_forward_command below) or the kind-specific
# ingress-nginx + extraPortMappings setup (see README.md), which is optional
# and only relevant if you've set your kind cluster up that way.

output "release_name" {
  description = "Name of the Helm release."
  value       = helm_release.ownfirebase.name
}

output "release_namespace" {
  description = "Namespace the release was installed into."
  value       = kubernetes_namespace_v1.ownfirebase.metadata[0].name
}

output "release_status" {
  description = "Release status as reported by Terraform after apply (e.g. deployed, failed, pending-install, pending-upgrade)."
  value       = helm_release.ownfirebase.status
}

output "release_version" {
  description = "Chart version Helm actually installed, as resolved from deploy/helm/ownfirebase/Chart.yaml."
  value       = helm_release.ownfirebase.metadata.version
}

output "secret_name" {
  description = "Name of the kubernetes_secret_v1 holding DJANGO_SECRET_KEY/DATABASE_PASSWORD/etc, for reference by kubectl or other manifests."
  value       = kubernetes_secret_v1.ownfirebase.metadata[0].name
}

output "port_forward_command" {
  description = <<-EOT
    kind has no real LoadBalancer, so this is the reliable way to reach the
    app from your host. Target port 8000 matches the chart's default
    web.service.port (deploy/helm/ownfirebase/values.yaml) — adjust both the
    service name and port if you've overridden either, confirm with:
      kubectl --context <kube_context> -n <namespace> get svc
  EOT
  value       = "kubectl --context ${var.kube_context} -n ${kubernetes_namespace_v1.ownfirebase.metadata[0].name} port-forward svc/${var.namespace}-web 8080:8000"
}

output "logs_command" {
  description = "Tail the Django app's logs while iterating locally."
  value       = "kubectl --context ${var.kube_context} -n ${kubernetes_namespace_v1.ownfirebase.metadata[0].name} logs -l app.kubernetes.io/component=web -f"
}
