# Infrastructure as Code - Terraform

Google Cloud Platform deployment configuration using Terraform.

## Overview

Terraform configuration for deploying UltraDL to Google Cloud Platform with:

- Compute Engine VM instance
- Google Cloud Storage bucket
- Automatic lifecycle rules
- Docker-based deployment
- Startup script automation

## Structure

```
terraform/
├── main.tf                  # Main Terraform configuration
├── variables.tf             # Input variables
├── outputs.tf               # Output values
├── terraform.tfvars.example # Example configuration
├── startup.sh               # VM startup script
├── Makefile                 # Terraform shortcuts
└── README.md                # This file
```

## Prerequisites

- Google Cloud Platform account
- `gcloud` CLI installed and configured
- Terraform installed (>= 1.0)
- GCP project with billing enabled
- Service account with appropriate permissions

## Required GCP APIs

Enable these APIs in your GCP project:

```bash
gcloud services enable compute.googleapis.com
gcloud services enable storage.googleapis.com
```

## Configuration

### 1. Create terraform.tfvars

```bash
cp terraform.tfvars.example terraform.tfvars
```

### 2. Edit terraform.tfvars

```hcl
project_id = "your-gcp-project-id"
region     = "us-central1"
zone       = "us-central1-a"

# VM Configuration
machine_type = "e2-medium"
disk_size_gb = 30

# Storage Configuration
bucket_name = "your-unique-bucket-name"
bucket_location = "US"

# Application Configuration
flask_env = "production"
```

## Deployment

### Initialize Terraform

```bash
terraform init
```

### Plan Deployment

```bash
terraform plan
```

### Apply Configuration

```bash
terraform apply
```

### Destroy Infrastructure

```bash
terraform destroy
```

## Makefile Commands

Convenient shortcuts for common operations:

```bash
# Initialize Terraform
make init

# Plan changes
make plan

# Apply changes
make apply

# Destroy infrastructure
make destroy

# Format Terraform files
make fmt

# Validate configuration
make validate

# Show current state
make show
```

## Resources Created

### Compute Engine VM

- **Name:** `ultradl-vm`
- **Machine Type:** e2-medium (configurable)
- **OS:** Ubuntu 22.04 LTS
- **Disk:** 30 GB (configurable)
- **Network:** Default VPC with external IP
- **Firewall:** HTTP (80), HTTPS (443), SSH (22)

### Google Cloud Storage

- **Bucket:** Configured name
- **Location:** US (configurable)
- **Lifecycle Rules:**
  - Delete files older than 1 day
  - Automatic cleanup of expired downloads

### Startup Script

The VM runs a startup script that:

1. Installs Docker and Docker Compose
2. Clones the repository
3. Configures environment variables
4. Starts all services
5. Sets up automatic restart on reboot

## Environment Variables

The startup script configures these variables:

```bash
FLASK_ENV=production
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
GCS_BUCKET_NAME=<your-bucket>
GOOGLE_APPLICATION_CREDENTIALS=/app/gcs-key.json
```

## Outputs

After deployment, Terraform outputs:

- `vm_external_ip` - Public IP address of the VM
- `vm_name` - Name of the VM instance
- `bucket_name` - Name of the GCS bucket
- `bucket_url` - URL of the GCS bucket

Access the application at: `http://<vm_external_ip>`

## Storage Configuration

### GCS Lifecycle Rules

Automatically configured:

```hcl
lifecycle_rule {
  condition {
    age = 1  # Delete after 1 day
  }
  action {
    type = "Delete"
  }
}
```

### Service Account

The VM uses a service account with:

- `storage.objects.create` - Upload files
- `storage.objects.delete` - Delete files
- `storage.objects.get` - Generate signed URLs

## Monitoring

### Check VM Status

```bash
# SSH into VM
gcloud compute ssh ultradl-vm --zone=us-central1-a

# Check Docker services
docker-compose ps

# View logs
docker-compose logs -f
```

### Check GCS Bucket

```bash
# List files
gsutil ls gs://your-bucket-name/

# Check lifecycle configuration
gsutil lifecycle get gs://your-bucket-name/
```

## Troubleshooting

### VM Not Starting

```bash
# Check startup script logs
gcloud compute instances get-serial-port-output ultradl-vm --zone=us-central1-a
```

### GCS Access Issues

```bash
# Verify service account permissions
gcloud projects get-iam-policy your-project-id

# Test bucket access
gsutil ls gs://your-bucket-name/
```

### Application Not Accessible

```bash
# Check firewall rules
gcloud compute firewall-rules list

# Verify VM external IP
gcloud compute instances describe ultradl-vm --zone=us-central1-a --format="get(networkInterfaces[0].accessConfigs[0].natIP)"
```

## Cost Estimation

**Monthly costs (approximate):**

- Compute Engine (e2-medium): ~$25/month
- Cloud Storage: ~$0.02/GB/month
- Network egress: Variable based on usage

**Total:** ~$25-30/month for light usage

## Security Considerations

1. **Firewall Rules:** Only necessary ports exposed (80, 443, 22)
2. **Service Account:** Minimal permissions (storage only)
3. **Signed URLs:** 10-minute expiration for downloads
4. **Rate Limiting:** Enabled in production mode
5. **Automatic Cleanup:** Files deleted after 1 day

## Scaling

For higher traffic, consider:

1. **Increase VM size:** Change `machine_type` in terraform.tfvars
2. **Add load balancer:** Distribute traffic across multiple VMs
3. **Use Cloud Run:** Serverless alternative for backend
4. **CDN:** Add Cloud CDN for static assets

## Backup and Recovery

### Backup VM

```bash
# Create snapshot
gcloud compute disks snapshot ultradl-vm --zone=us-central1-a
```

### Restore from Snapshot

```bash
# Create disk from snapshot
gcloud compute disks create ultradl-vm-restored --source-snapshot=<snapshot-name>
```

## Testing

Test lifecycle rules:

```bash
cd terraform
python docs/test_lifecycle.py
```

## Additional Resources

- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [GCP Compute Engine](https://cloud.google.com/compute/docs)
- [GCS Lifecycle Management](https://cloud.google.com/storage/docs/lifecycle)
