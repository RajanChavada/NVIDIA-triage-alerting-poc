# NVIDIA Triage Agent Infrastructure
# 
# This Terraform configuration provisions the complete infrastructure:
# - GPU-enabled Kubernetes cluster
# - Prometheus + DCGM Exporter monitoring stack
# - Kafka brokers for event streaming
# - PostgreSQL for incident storage

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.25"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
  }
}

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "cluster_name" {
  description = "Name of the GKE cluster"
  type        = string
  default     = "triage-agents-prod"
}

variable "gpu_node_count" {
  description = "Number of GPU nodes"
  type        = number
  default     = 3
}

variable "gpu_type" {
  description = "Type of GPU accelerator"
  type        = string
  default     = "nvidia-tesla-t4"
}

# -----------------------------------------------------------------------------
# GKE Cluster with GPU Support
# -----------------------------------------------------------------------------

resource "google_container_cluster" "primary" {
  name     = var.cluster_name
  location = var.region
  
  # We can't create a cluster with no node pool, so we create a minimal one
  # then immediately delete it and create our own managed pools
  remove_default_node_pool = true
  initial_node_count       = 1
  
  # Enable Workload Identity
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
  
  # Enable Network Policy
  network_policy {
    enabled = true
  }
  
  # Enable logging and monitoring
  logging_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  }
  
  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS"]
    managed_prometheus {
      enabled = true
    }
  }
}

# CPU node pool for control plane and lightweight workloads
resource "google_container_node_pool" "cpu_pool" {
  name       = "cpu-pool"
  location   = var.region
  cluster    = google_container_cluster.primary.name
  node_count = 2
  
  node_config {
    machine_type = "e2-standard-4"
    
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    
    labels = {
      "workload-type" = "general"
    }
    
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }
}

# GPU node pool for inference workloads
resource "google_container_node_pool" "gpu_pool" {
  name       = "gpu-pool"
  location   = var.region
  cluster    = google_container_cluster.primary.name
  node_count = var.gpu_node_count
  
  node_config {
    machine_type = "n1-standard-8"
    
    guest_accelerator {
      type  = var.gpu_type
      count = 1
      gpu_driver_installation_config {
        gpu_driver_version = "LATEST"
      }
    }
    
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    
    labels = {
      "workload-type"     = "gpu"
      "nvidia.com/gpu"    = "true"
    }
    
    taint {
      key    = "nvidia.com/gpu"
      value  = "present"
      effect = "NO_SCHEDULE"
    }
    
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }
}

# -----------------------------------------------------------------------------
# Helm Charts for Monitoring Stack
# -----------------------------------------------------------------------------

# Install NVIDIA GPU Operator
resource "helm_release" "gpu_operator" {
  name       = "gpu-operator"
  repository = "https://helm.ngc.nvidia.com/nvidia"
  chart      = "gpu-operator"
  namespace  = "gpu-operator"
  create_namespace = true
  
  values = [
    <<-EOT
    driver:
      enabled: false  # Using GKE auto-installed drivers
    toolkit:
      enabled: true
    dcgm:
      enabled: true
    dcgmExporter:
      enabled: true
      serviceMonitor:
        enabled: true
    EOT
  ]
  
  depends_on = [google_container_node_pool.gpu_pool]
}

# Install Prometheus Stack
resource "helm_release" "prometheus" {
  name       = "prometheus"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  namespace  = "monitoring"
  create_namespace = true
  
  values = [
    <<-EOT
    prometheus:
      prometheusSpec:
        retention: 30d
        serviceMonitorSelectorNilUsesHelmValues: false
        additionalScrapeConfigs:
          - job_name: 'dcgm-exporter'
            kubernetes_sd_configs:
              - role: endpoints
            relabel_configs:
              - source_labels: [__meta_kubernetes_service_label_app]
                regex: dcgm-exporter
                action: keep
    alertmanager:
      config:
        receivers:
          - name: 'pagerduty'
            pagerduty_configs:
              - service_key_file: /etc/alertmanager/secrets/pagerduty-key
    grafana:
      enabled: true
      dashboardProviders:
        dashboardproviders.yaml:
          apiVersion: 1
          providers:
            - name: 'gpu-dashboards'
              folder: 'GPU'
              type: file
              options:
                path: /var/lib/grafana/dashboards/gpu
    EOT
  ]
  
  depends_on = [google_container_node_pool.cpu_pool]
}

# Install Kafka
resource "helm_release" "kafka" {
  name       = "kafka"
  repository = "https://charts.bitnami.com/bitnami"
  chart      = "kafka"
  namespace  = "kafka"
  create_namespace = true
  
  values = [
    <<-EOT
    replicaCount: 3
    zookeeper:
      enabled: true
      replicaCount: 3
    persistence:
      enabled: true
      size: 100Gi
    provisioning:
      enabled: true
      topics:
        - name: gpu-alerts
          partitions: 3
          replicationFactor: 3
        - name: triage-outcomes
          partitions: 3
          replicationFactor: 3
        - name: agent-diagnostics
          partitions: 1
          replicationFactor: 2
    EOT
  ]
  
  depends_on = [google_container_node_pool.cpu_pool]
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = google_container_cluster.primary.endpoint
  sensitive   = true
}

output "cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.primary.name
}

output "gpu_node_pool" {
  description = "GPU node pool name"
  value       = google_container_node_pool.gpu_pool.name
}
