output "cloud_run_url" {
  description = "The public endpoint URL of the deployed Paper2Patent API."
  value       = google_cloud_run_v2_service.api_service.uri
}

output "storage_bucket_name" {
  description = "Google Cloud Storage bucket for saving patent dossiers."
  value       = google_storage_bucket.patent_dossiers.name
}

output "artifact_registry_repo" {
  description = "Artifact Registry Docker repository path."
  value       = google_artifact_registry_repository.agent_repo.name
}
