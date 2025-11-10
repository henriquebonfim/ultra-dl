# Terraform configuration for UltraDL YouTube Downloader
# GCP Free Tier deployment with GCS lifecycle management

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Configure the Google Cloud Provider
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# GCS Bucket for temporary download files
resource "google_storage_bucket" "downloads" {
  name          = var.bucket_name
  location      = var.bucket_location
  force_destroy = true  # Allow bucket deletion even with objects
  
  # Uniform bucket-level access for simplified IAM
  uniform_bucket_level_access {
    enabled = true
  }
  
  # Lifecycle rules for automatic cleanup
  lifecycle_rule {
    # Delete objects after 1 day
    condition {
      age = 1
    }
    action {
      type = "Delete"
    }
  }
  
  lifecycle_rule {
    # Clean up incomplete multipart uploads after 1 day
    condition {
      age                        = 1
      matches_prefix             = []
      with_state                 = "ANY"
      num_newer_versions         = 0
    }
    action {
      type = "AbortIncompleteMultipartUpload"
    }
  }
  
  # CORS configuration for direct browser downloads
  cors {
    origin          = var.cors_origins
    method          = ["GET", "HEAD"]
    response_header = ["Content-Type", "Content-Disposition"]
    max_age_seconds = 3600
  }
  
  # Labels for resource management
  labels = {
    environment = var.environment
    application = "ultradl-youtube-downloader"
    managed_by  = "terraform"
  }
}

# Service account for the application
resource "google_service_account" "app_service_account" {
  account_id   = var.service_account_name
  display_name = "UltraDL Application Service Account"
  description  = "Service account for UltraDL YouTube Downloader application"
}

# IAM binding for GCS bucket access
resource "google_storage_bucket_iam_member" "app_bucket_admin" {
  bucket = google_storage_bucket.downloads.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.app_service_account.email}"
}

# Service account key for application authentication
resource "google_service_account_key" "app_key" {
  service_account_id = google_service_account.app_service_account.name
}

# Compute Engine instance (e2-micro for free tier)
resource "google_compute_instance" "youtube_downloader" {
  name         = var.instance_name
  machine_type = "e2-micro"  # Free tier eligible
  zone         = var.zone
  
  # Allow instance to be stopped for updates
  allow_stopping_for_update = true
  
  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
      size  = 30  # GB, within free tier
      type  = "pd-standard"
    }
  }
  
  network_interface {
    network = "default"
    
    access_config {
      # Ephemeral public IP
    }
  }
  
  # Service account for GCS access
  service_account {
    email  = google_service_account.app_service_account.email
    scopes = ["cloud-platform"]
  }
  
  # Startup script to install Docker and dependencies
  metadata_startup_script = file("${path.module}/startup.sh")
  
  # Metadata for configuration
  metadata = {
    gcs-bucket-name = google_storage_bucket.downloads.name
  }
  
  tags = ["http-server", "https-server"]
  
  labels = {
    environment = var.environment
    application = "ultradl-youtube-downloader"
    managed_by  = "terraform"
  }
}

# Firewall rule for HTTP traffic
resource "google_compute_firewall" "allow_http" {
  name    = "${var.instance_name}-allow-http"
  network = "default"
  
  allow {
    protocol = "tcp"
    ports    = ["80", "8080"]
  }
  
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["http-server"]
}

# Firewall rule for HTTPS traffic
resource "google_compute_firewall" "allow_https" {
  name    = "${var.instance_name}-allow-https"
  network = "default"
  
  allow {
    protocol = "tcp"
    ports    = ["443"]
  }
  
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["https-server"]
}
