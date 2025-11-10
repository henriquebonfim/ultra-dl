# Variables for UltraDL YouTube Downloader Terraform configuration

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone for compute instance"
  type        = string
  default     = "us-central1-a"
}

variable "bucket_name" {
  description = "Name of the GCS bucket for temporary downloads"
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-_]{1,61}[a-z0-9]$", var.bucket_name))
    error_message = "Bucket name must be 3-63 characters, lowercase letters, numbers, hyphens, and underscores only."
  }
}

variable "bucket_location" {
  description = "Location for the GCS bucket (US, EU, ASIA, or specific region)"
  type        = string
  default     = "US"
}

variable "cors_origins" {
  description = "Allowed CORS origins for direct browser downloads"
  type        = list(string)
  default     = ["*"]
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "service_account_name" {
  description = "Name for the application service account"
  type        = string
  default     = "ultradl-app-sa"
}

variable "instance_name" {
  description = "Name for the Compute Engine instance"
  type        = string
  default     = "youtube-downloader-vm"
}
