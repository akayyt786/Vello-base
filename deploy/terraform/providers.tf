# providers.tf — Terraform + provider configuration for the OwnFirebase
# Helm deployment.
#
# This module talks to Kubernetes exclusively through the *local kubeconfig*
# (defaults to ~/.kube/config) plus a context name (var.kube_context). No
# cluster endpoint, token, or CA cert is hardcoded anywhere in this module —
# that is what makes it work unmodified against:
#   - a local `kind` cluster (the supported, testable-here target), and
#   - a real cloud cluster (EKS/GKE/AKS/etc.) once its kubeconfig context is
#     merged locally (see README.md "Cloud extension" section) — you'd just
#     change `kube_context`, nothing else in this module.
#
# Provider versions were verified against what actually installs today
# (`terraform init` resolved helm ~> 3.2 and kubernetes ~> 3.2). Both
# providers had a breaking rewrite at major version 3 vs the older 2.x
# generation (e.g. helm_release's `set`/`set_sensitive` became list-of-object
# attributes instead of repeated blocks). This module is written against and
# pinned to the 3.x schema — do not loosen the version constraints below to
# allow 2.x without rewriting main.tf's `set`/`set_sensitive` usage.

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = "~> 3.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 3.0"
    }
  }
}

provider "kubernetes" {
  config_path    = pathexpand(var.kubeconfig_path)
  config_context = var.kube_context
}

provider "helm" {
  kubernetes = {
    config_path    = pathexpand(var.kubeconfig_path)
    config_context = var.kube_context
  }
}
