terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Artifact Registry Repository for Docker Images
resource "google_artifact_registry_repository" "agent_repo" {
  location      = var.region
  repository_id = "paper2patent-containers"
  description   = "Docker repository for Paper2Patent Google ADK Multi-Agent services"
  format        = "DOCKER"
}

# 2. Google Cloud Storage Bucket for Generated Patent Dossiers
resource "google_storage_bucket" "patent_dossiers" {
  name          = "${var.project_id}-patent-dossiers"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}

# 3. Secret Manager for Gemini API Key
resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "gemini-api-key"

  replication {
    auto {}
  }
}

# 4. Cloud Run Service for Paper2Patent ADK API
resource "google_cloud_run_v2_service" "api_service" {
  name     = "paper2patent-adk-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.agent_repo.name}/paper2patent-api:latest"

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }

      ports {
        container_port = 8000
      }

      env {
        name  = "MODEL_NAME"
        value = var.model_name
      }

      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }

      env {
        name  = "FALLBACK_TO_MOCK"
        value = "true"
      }

      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8000
        }
        initial_delay_seconds = 5
        period_seconds        = 10
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }
  }

  depends_on = [
    google_artifact_registry_repository.agent_repo,
    google_secret_manager_secret.gemini_api_key,
  ]
}

# 5. IAM Policy for Public Access to API (Optional)
resource "google_cloud_run_service_iam_binding" "public_access" {
  location = google_cloud_run_v2_service.api_service.location
  service  = google_cloud_run_v2_service.api_service.name
  role     = "roles/run.invoker"
  members = [
    "allUsers"
  ]
}
