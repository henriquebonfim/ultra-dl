#!/bin/bash
# Clean up build, cache, and instance directories

find . -type d -name "venv" -exec rm -rf {} +
find . -type d -name ".venv" -exec rm -rf {} +
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type d -name "*_cache" -exec rm -rf {} +
find . -type d -name ".pytest_cache" -exec rm -rf {} +
find . -type d -name ".mypy_cache" -exec rm -rf {} +
find . -type d -name ".tox" -exec rm -rf {} +
find . -type d -name "htmlcov" -exec rm -rf {} +
find . -type d -name "build" -exec rm -rf {} +
find . -type d -name "*.egg*" -exec rm -rf {} +
find . -type d -name "instance" -exec rm -rf {} +
find . -type d -name "migrations" -exec rm -rf {} +
find . -type d -name "node_modules" -exec rm -rf {} +
find . -type d -name ".expo" -exec rm -rf {} +
find . -type d -name ".idea" -exec rm -rf {} +
find . -type d -name "dev-dist" -exec rm -rf {} +
find . -type d -name "dist" -exec rm -rf {} +
find . -type d -name ".next" -exec rm -rf {} +
find . -type d -name ".nuxt" -exec rm -rf {} +
find . -type d -name ".cache" -exec rm -rf {} +
find . -type d -name ".parcel-cache" -exec rm -rf {} +
find . -type d -name ".vite" -exec rm -rf {} +
find . -type d -name ".terraform" -exec rm -rf {} +
find . -type f -name ".DS_Store" -exec rm {} +
find . -type f -name "Thumbs.db" -exec rm {} +
find . -type f -name "*.log" -exec rm {} +
find . -type f -name "*.tmp" -exec rm {} +
find . -type d -name ".coverage" -exec rm -rf {} +
find . -type f -name ".coverage" -exec rm {} +
find . -type f -name "*:Zone.Identifier" -exec rm {} +
find . -type f -name "terraform.tfstate*" -exec rm {} +
find . -type f -name ".terraform.lock.hcl" -exec rm {} +
