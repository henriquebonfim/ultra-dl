# Outputs for UltraDL YouTube Downloader Terraform configuration

output "bucket_name" {
  description = "Name of the GCS bucket for downloads"
  value       = google_storage_bucket.downloads.name
}

output "bucket_url" {
  description = "URL of the GCS bucket"
  value       = google_storage_bucket.downloads.url
}

output "service_account_email" {
  description = "Email of the application service account"
  value       = google_service_account.app_service_account.email
}

output "service_account_key" {
  description = "Base64 encoded service account key (sensitive)"
  value       = google_service_account_key.app_key.private_key
  sensitive   = true
}

output "instance_name" {
  description = "Name of the Compute Engine instance"
  value       = google_compute_instance.youtube_downloader.name
}

output "instance_external_ip" {
  description = "External IP address of the Compute Engine instance"
  value       = google_compute_instance.youtube_downloader.network_interface[0].access_config[0].nat_ip
}

output "instance_internal_ip" {
  description = "Internal IP address of the Compute Engine instance"
  value       = google_compute_instance.youtube_downloader.network_interface[0].network_ip
}

output "lifecycle_rules_summary" {
  description = "Summary of GCS lifecycle rules configured"
  value = {
    object_deletion_age_days           = 1
    multipart_upload_cleanup_age_days  = 1
  }
}
