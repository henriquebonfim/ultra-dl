.PHONY: help init plan apply destroy validate fmt check test-lifecycle clean

# Default target
help:
	@echo "UltraDL YouTube Downloader - Terraform Commands"
	@echo ""
	@echo "Available targets:"
	@echo "  init            - Initialize Terraform"
	@echo "  plan            - Show execution plan"
	@echo "  apply           - Apply infrastructure changes"
	@echo "  destroy         - Destroy all infrastructure"
	@echo "  validate        - Validate Terraform configuration"
	@echo "  fmt             - Format Terraform files"
	@echo "  check           - Run validation and formatting checks"
	@echo "  test-lifecycle  - Test GCS lifecycle rules"
	@echo "  clean           - Clean Terraform state and cache"
	@echo ""
	@echo "Usage examples:"
	@echo "  make init"
	@echo "  make plan"
	@echo "  make apply"
	@echo "  make test-lifecycle"

# Initialize Terraform
init:
	@echo "Initializing Terraform..."
	terraform init

# Show execution plan
plan:
	@echo "Creating execution plan..."
	terraform plan

# Apply infrastructure changes
apply:
	@echo "Applying infrastructure changes..."
	terraform apply

# Destroy all infrastructure
destroy:
	@echo "Destroying infrastructure..."
	terraform destroy

# Validate Terraform configuration
validate:
	@echo "Validating Terraform configuration..."
	terraform validate

# Format Terraform files
fmt:
	@echo "Formatting Terraform files..."
	terraform fmt -recursive

# Run all checks
check: validate fmt
	@echo "All checks passed!"

# Test GCS lifecycle rules
test-lifecycle:
	@echo "Testing GCS lifecycle rules..."
	@if [ ! -f terraform.tfstate ]; then \
		echo "Error: No Terraform state found. Run 'make apply' first."; \
		exit 1; \
	fi
	@BUCKET_NAME=$$(terraform output -raw bucket_name 2>/dev/null); \
	if [ -z "$$BUCKET_NAME" ]; then \
		echo "Error: Could not get bucket name from Terraform output"; \
		exit 1; \
	fi; \
	echo "Testing bucket: $$BUCKET_NAME"; \
	python3 docs/test_lifecycle.py $$BUCKET_NAME

# Test with file upload
test-lifecycle-upload:
	@echo "Testing GCS lifecycle rules with file upload..."
	@BUCKET_NAME=$$(terraform output -raw bucket_name 2>/dev/null); \
	if [ -z "$$BUCKET_NAME" ]; then \
		echo "Error: Could not get bucket name from Terraform output"; \
		exit 1; \
	fi; \
	python3 docs/test_lifecycle.py $$BUCKET_NAME --upload

# Verify lifecycle execution
test-lifecycle-verify:
	@echo "Verifying GCS lifecycle rule execution..."
	@BUCKET_NAME=$$(terraform output -raw bucket_name 2>/dev/null); \
	if [ -z "$$BUCKET_NAME" ]; then \
		echo "Error: Could not get bucket name from Terraform output"; \
		exit 1; \
	fi; \
	python3 docs/test_lifecycle.py $$BUCKET_NAME --verify

# Clean Terraform state and cache
clean:
	@echo "Cleaning Terraform state and cache..."
	rm -rf .terraform/
	rm -f .terraform.lock.hcl
	rm -f terraform.tfstate.backup
	@echo "Note: terraform.tfstate was not deleted for safety"
	@echo "To remove it manually: rm terraform.tfstate"

# Show outputs
outputs:
	@echo "Terraform outputs:"
	@terraform output

# Get service account key
get-key:
	@echo "Extracting service account key..."
	@terraform output -raw service_account_key > service-account-key.json
	@chmod 600 service-account-key.json
	@echo "Service account key saved to: service-account-key.json"
	@echo "Permissions set to 600 (owner read/write only)"
