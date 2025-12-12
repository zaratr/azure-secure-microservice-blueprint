# Azure Secure Microservice Blueprint

A cloud-native, zero-trust aligned reference implementation using FastAPI + worker microservice, Azure Service Bus, Azure Storage, and PostgreSQL. Includes Terraform to deploy to Azure Container Apps with managed identity and private networking.

## Architecture
```
+-------------+        +------------------+         +----------------+
|  Client     | --->   | FastAPI (API)    |  --->   | Service Bus    |
|  (ingress)  |        |  - rate limit    |         | Queue          |
+-------------+        |  - validation    |         +----------------+
       |               |  - MI auth       |                   |
       v               +------------------+                   v
                  +----------- VNet / Private Endpoints -------------+
                  |                                                |
                  |  Container Apps Worker -> Blob Storage (PE)    |
                  |                |                               |
                  |                v                               |
                  |            PostgreSQL (PE)                     |
                  +------------------------------------------------+
```

### Security Posture
* **Identity-first**: services use Azure Managed Identity for Service Bus, Storage, and database access (no secrets in code). Local dev uses `.env` only.
* **Zero-trust networking**: VNet with subnets per service, private endpoints for Storage and Postgres; only the API ingress is public.
* **Secrets**: none in repo; runtime config via environment or managed identity.

## Local Development
1. Copy `.env.example` to `.env` and adjust values as needed.
2. Start stack:
   ```bash
   docker-compose up --build
   ```
3. Create a job:
   ```bash
   curl -X POST http://localhost:8000/jobs \
     -H "Content-Type: application/json" \
     -d '{"document_url": "https://example.com/doc.pdf"}'
   ```
4. Check status:
   ```bash
   curl http://localhost:8000/jobs/<job_id>
   ```

## Cloud Deployment (Terraform + Azure Container Apps)
1. Install Terraform and Azure CLI; login with `az login`.
2. `cd infra/terraform` and copy `terraform.tfvars.example` to `terraform.tfvars` with your values.
3. Deploy:
   ```bash
   terraform init
   terraform apply
   ```
4. Outputs include Container Apps endpoint and connection info. Services run with managed identity; Service Bus/Storage/Postgres use private endpoints.

## Observability
* OpenTelemetry SDK is wired for OTLP endpoint (App Insights exporter supported via Azure Monitor agent).
* Structured JSON logging via structlog.
* Health endpoint: `GET /health`.

## Production Readiness Checklist
- [x] Structured logging & tracing hooks
- [x] Rate limiting and correlation IDs
- [x] Retries + DLQ (Service Bus) documented
- [x] Health checks
- [x] IaC for repeatable deploy

## Testing
Run from repo root:
```bash
cd services/api && poetry install && pytest
cd ../worker && poetry install && pytest
```

