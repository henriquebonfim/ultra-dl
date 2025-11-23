# Infrastructure - Task Tracker

> **Purpose**: Infrastructure-specific tasks following Terraform module patterns. For cross-cutting tasks, see [../todo.md](../todo.md).

**Last Updated**: November 11, 2025
**Priority**: High = 🔴 | Medium = 🟡 | Low = 🟢

---

## 🔴 Priority 1: Documentation Compression ✅ COMPLETE

### REQ-IAC-DOC-1: Compress ARCHITECTURE.md ✅

**The system shall** reduce iac/ARCHITECTURE.md from 441 lines to maximum 300 lines.

**Tasks**:
- [x] ✅ Simplify GCP architecture diagram
- [x] ✅ Remove verbose Terraform explanations
- [x] ✅ Add Terraform module composition diagram
- [x] ✅ Keep: Module structure, resource organization, best practices
- [x] ✅ Remove: Detailed configuration examples, redundant sections

**Target**: 300 lines max
**Original**: 441 lines
**Final**: 300 lines
**Reduction**: 141 lines (32.0%)

---

### REQ-IAC-DOC-2: Compress AGENTS.md ✅

**The system shall** reduce iac/AGENTS.md from 375 lines to maximum 300 lines.

**Tasks**:
- [x] ✅ Update for module-based workflow
- [x] ✅ Consolidate workflow sections
- [x] ✅ Add module development patterns
- [x] ✅ Keep: Core patterns, best practices, testing guidelines
- [x] ✅ Remove: Verbose examples, redundant explanations

**Target**: 300 lines max
**Original**: 375 lines
**Final**: 264 lines
**Reduction**: 111 lines (29.6%)

---

## 🔴 Priority 2: Terraform Module Structure

### REQ-IAC-MOD-1: Create Module Structure

**WHEN** infrastructure is provisioned, **THEN** the system shall use reusable Terraform modules with composition pattern: root module + child modules (compute, storage, network).

**Phase 1: Create Module Directories** 🔴 HIGH PRIORITY

**Tasks**:
- [ ] Create module structure:
  ```bash
  cd iac
  mkdir -p modules/{compute,storage,network}
  ```

- [ ] Create standard files for each module:
  ```bash
  # Compute module
  touch modules/compute/{main.tf,variables.tf,outputs.tf,README.md}

  # Storage module
  touch modules/storage/{main.tf,variables.tf,outputs.tf,README.md}

  # Network module
  touch modules/network/{main.tf,variables.tf,outputs.tf,README.md}
  ```

- [ ] Document module structure in ARCHITECTURE.md

**Status**: Structure planned, not yet created

---

### REQ-IAC-MOD-2: Create Compute Module

**Phase 2: Extract Resources to Modules** 🟡 MEDIUM PRIORITY

**Tasks**:

**Compute Module** (`modules/compute/`)

- [ ] Create `main.tf`:
  ```hcl
  # VM instance resource
  resource "google_compute_instance" "app_instance" {
    name         = var.instance_name
    machine_type = var.machine_type
    zone         = var.zone

    boot_disk {
      initialize_params {
        image = var.boot_image
        size  = var.disk_size
      }
    }

    network_interface {
      network    = var.network
      subnetwork = var.subnetwork
      access_config {
        // Ephemeral public IP
      }
    }

    metadata_startup_script = var.startup_script

    tags = var.tags
  }
  ```

- [ ] Create `variables.tf` with validation:
  ```hcl
  variable "instance_name" {
    description = "Name of the VM instance"
    type        = string

    validation {
      condition     = can(regex("^[a-z][a-z0-9-]{0,61}[a-z0-9]$", var.instance_name))
      error_message = "Instance name must be 1-63 lowercase letters, numbers, or hyphens."
    }
  }

  variable "machine_type" {
    description = "VM machine type"
    type        = string
    default     = "e2-medium"
  }

  variable "zone" {
    description = "GCP zone"
    type        = string
  }

  variable "boot_image" {
    description = "Boot disk image"
    type        = string
    default     = "ubuntu-2204-lts"
  }

  variable "disk_size" {
    description = "Boot disk size in GB"
    type        = number
    default     = 50

    validation {
      condition     = var.disk_size >= 10 && var.disk_size <= 1000
      error_message = "Disk size must be between 10 and 1000 GB."
    }
  }

  variable "startup_script" {
    description = "Startup script for VM initialization"
    type        = string
  }

  variable "network" {
    description = "Network name"
    type        = string
  }

  variable "subnetwork" {
    description = "Subnetwork name"
    type        = string
  }

  variable "tags" {
    description = "Network tags for firewall rules"
    type        = list(string)
    default     = []
  }
  ```

- [ ] Create `outputs.tf`:
  ```hcl
  output "instance_id" {
    description = "ID of the compute instance"
    value       = google_compute_instance.app_instance.id
  }

  output "instance_name" {
    description = "Name of the compute instance"
    value       = google_compute_instance.app_instance.name
  }

  output "public_ip" {
    description = "Public IP address of the instance"
    value       = google_compute_instance.app_instance.network_interface[0].access_config[0].nat_ip
  }

  output "private_ip" {
    description = "Private IP address of the instance"
    value       = google_compute_instance.app_instance.network_interface[0].network_ip
  }
  ```

- [ ] Create `README.md` with module documentation

---

### REQ-IAC-MOD-3: Create Storage Module

**Storage Module** (`modules/storage/`)

**Tasks**:

- [ ] Create `main.tf`:
  ```hcl
  resource "google_storage_bucket" "file_storage" {
    name          = var.bucket_name
    location      = var.location
    storage_class = var.storage_class

    uniform_bucket_level_access = true

    versioning {
      enabled = var.enable_versioning
    }

    lifecycle_rule {
      condition {
        age = var.file_expiry_days
      }
      action {
        type = "Delete"
      }
    }

    cors {
      origin          = var.cors_origins
      method          = var.cors_methods
      response_header = ["Content-Type"]
      max_age_seconds = 3600
    }
  }

  resource "google_storage_bucket_iam_member" "public_access" {
    count  = var.enable_public_access ? 1 : 0
    bucket = google_storage_bucket.file_storage.name
    role   = "roles/storage.objectViewer"
    member = "allUsers"
  }
  ```

- [ ] Create `variables.tf` with validation
- [ ] Create `outputs.tf`
- [ ] Create `README.md`

---

### REQ-IAC-MOD-4: Create Network Module

**Network Module** (`modules/network/`)

**Tasks**:

- [ ] Create `main.tf` with VPC and firewall resources
- [ ] Create `variables.tf` with validation
- [ ] Create `outputs.tf`
- [ ] Create `README.md`

---

### REQ-IAC-MOD-5: Configure Root Module

**Phase 3: Configure Root Module** 🟡 MEDIUM PRIORITY

**Tasks**:

- [ ] Update `main.tf` to compose modules:
  ```hcl
  # Network module
  module "network" {
    source = "./modules/network"

    project_id = var.project_id
    region     = var.region
    # ... other variables
  }

  # Storage module
  module "storage" {
    source = "./modules/storage"

    bucket_name     = var.gcs_bucket_name
    location        = var.region
    file_expiry_days = var.file_expiry_minutes / (24 * 60)
    # ... other variables
  }

  # Compute module
  module "compute" {
    source = "./modules/compute"

    instance_name  = var.instance_name
    machine_type   = var.machine_type
    zone           = var.zone
    network        = module.network.network_name
    subnetwork     = module.network.subnetwork_name
    startup_script = file("${path.module}/startup.sh")
    # ... other variables

    depends_on = [module.network, module.storage]
  }
  ```

- [ ] Create/update `backend.tf` for remote state:
  ```hcl
  terraform {
    backend "gcs" {
      bucket = "ultra-dl-terraform-state"
      prefix = "terraform/state"
    }
  }
  ```

- [ ] Create/update `versions.tf`:
  ```hcl
  terraform {
    required_version = ">= 1.5"

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
  ```

- [ ] Update `variables.tf` to use module variables
- [ ] Update `outputs.tf` to expose module outputs

---

### REQ-IAC-MOD-6: Module Documentation

**Phase 4: Documentation** 🟢 LOW PRIORITY

**Tasks**:

- [ ] Document each module in README.md:
  - Purpose and usage
  - Input variables with examples
  - Outputs with descriptions
  - Example usage code
  - Requirements (Terraform version, providers)

- [ ] Update iac/ARCHITECTURE.md:
  - Add module composition diagram
  - Document module dependencies
  - Explain module best practices

- [ ] Update iac/AGENTS.md:
  - Add module development workflow
  - Document testing procedures
  - Add troubleshooting guide

- [ ] Create examples/ directory:
  ```bash
  mkdir -p examples/{basic,advanced}
  ```
  - [ ] Add basic example (single VM + bucket)
  - [ ] Add advanced example (HA setup)

---

## 🟡 Priority 3: Security Enhancements

### REQ-IAC-SEC-1: Credential Management

**WHERE** production environment, **THEN** the system shall use Google Secret Manager for sensitive configuration.

**Tasks**:
- [ ] Create Secret Manager resources:
  ```hcl
  resource "google_secret_manager_secret" "gcs_credentials" {
    secret_id = "gcs-credentials"

    replication {
      automatic = true
    }
  }
  ```

- [ ] Migrate GCS credentials to Secret Manager
- [ ] Update startup script to fetch secrets
- [ ] Document secret rotation procedure
- [ ] Add IAM policies for secret access

---

### REQ-IAC-SEC-2: Network Security

**Tasks**:
- [ ] Implement least privilege firewall rules
- [ ] Configure VPC flow logs
- [ ] Enable Cloud Armor (DDoS protection)
- [ ] Add private Google access
- [ ] Configure NAT gateway for private instances

---

## 🟡 Priority 4: Infrastructure Testing

### REQ-IAC-TEST-1: Terraform Validation

**The system shall** validate Terraform configurations before applying.

**Tasks**:
- [ ] Add pre-commit hooks:
  ```bash
  # .pre-commit-config.yaml
  repos:
    - repo: https://github.com/antonbabenko/pre-commit-terraform
      hooks:
        - id: terraform_fmt
        - id: terraform_validate
        - id: terraform_docs
        - id: terraform_tflint
  ```

- [ ] Add Makefile targets:
  ```makefile
  .PHONY: validate
  validate:
  	terraform fmt -check
  	terraform validate
  	tflint

  .PHONY: plan
  plan:
  	terraform plan -out=tfplan

  .PHONY: apply
  apply:
  	terraform apply tfplan
  ```

- [ ] Add CI/CD pipeline for validation
- [ ] Run `terraform fmt` on all files
- [ ] Run `terraform validate` before PRs

---

### REQ-IAC-TEST-2: Infrastructure Testing

**Tasks**:
- [ ] Set up Terratest for module testing
- [ ] Write tests for each module
- [ ] Add integration tests
- [ ] Test failure scenarios
- [ ] Document testing procedures

---

## 🟡 Priority 5: Monitoring & Logging

### REQ-IAC-MON-1: Monitoring Setup

**Tasks**:
- [ ] Configure Cloud Monitoring
- [ ] Add VM health checks
- [ ] Configure alerting policies:
  - CPU usage > 80%
  - Disk usage > 90%
  - Memory usage > 80%
  - Service down
- [ ] Set up notification channels
- [ ] Create monitoring dashboard

---

### REQ-IAC-MON-2: Logging Configuration

**Tasks**:
- [ ] Enable Cloud Logging
- [ ] Configure log retention (30 days)
- [ ] Set up log-based metrics
- [ ] Add structured logging
- [ ] Create log analysis queries

---

## 🟢 Priority 6: Cost Optimization

### REQ-IAC-COST-1: Resource Optimization

**Tasks**:
- [ ] Use preemptible VMs for development
- [ ] Configure auto-shutdown for dev instances
- [ ] Implement GCS lifecycle policies
- [ ] Use committed use discounts
- [ ] Add cost monitoring alerts

---

### REQ-IAC-COST-2: Cost Tracking

**Tasks**:
- [ ] Add cost labels to all resources
- [ ] Set up cost breakdown reports
- [ ] Configure budget alerts
- [ ] Document cost optimization strategies

---

## 🟢 Priority 7: High Availability

### REQ-IAC-HA-1: Multi-Region Setup

**Tasks** (Future Enhancement):
- [ ] Create multi-region module
- [ ] Add load balancer
- [ ] Configure health checks
- [ ] Add auto-scaling
- [ ] Document HA architecture

---

## 📊 Progress Tracking

### Completed ✅
- [x] Terraform configuration for GCP
- [x] Compute Engine VM setup
- [x] Cloud Storage bucket
- [x] Basic networking (VPC, firewall)
- [x] Startup script for Docker setup
- [x] Manual deployment working
- [x] Documentation compression (2 files: ARCHITECTURE.md, AGENTS.md)

### In Progress ⚠️
- [ ] Terraform modularization (4 phases planned)

### Blocked 🚫
- Module Phase 2-4 (blocked by Phase 1 completion)

---

## 🔗 Related Documentation

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Infrastructure architecture
- **[AGENTS.md](./AGENTS.md)** - IaC AI agent guidelines
- **[README.md](./README.md)** - Infrastructure overview
- **[../todo.md](../todo.md)** - Root-level consolidated tasks
- **[../architecture.md](../architecture.md)** - System-wide architecture
