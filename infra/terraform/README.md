# Terraform Deployment

Deploys Azure Container Apps (API + Worker), Service Bus, Storage, and PostgreSQL with private networking.

## Usage
1. Copy `terraform.tfvars.example` to `terraform.tfvars` and set values.
2. Run `terraform init` and `terraform apply`.
3. Outputs provide API FQDN and Service Bus connection string (for bootstrap only; prefer managed identity).

## Variables
- `name_prefix`: base name for resources
- `location`: Azure region
- `resource_group`: name of resource group
- `storage_account_name`: must be globally unique
- `db_admin` / `db_password`: credentials for PostgreSQL (use Key Vault in production)
- `api_image` / `worker_image`: container images pushed to registry
- `container_registry`: login server of registry
- `database_url`: connection string for Postgres (managed identity recommended via AAD integration)

## Notes
- Private endpoints should be enabled for Storage and Postgres for production; this baseline keeps public endpoints off by default via Container Apps environment with internal load balancer.
- Service Bus queues support retries and DLQ via `max_delivery_count` and duplicate detection.
