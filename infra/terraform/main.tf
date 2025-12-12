terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "rg" {
  name     = var.resource_group
  location = var.location
}

resource "azurerm_virtual_network" "vnet" {
  name                = "${var.name_prefix}-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_subnet" "containerapps" {
  name                 = "containerapps"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]
  delegations {
    name = "appsvc"
    service_delegation {
      name = "Microsoft.App/environments"
    }
  }
}

resource "azurerm_log_analytics_workspace" "law" {
  name                = "${var.name_prefix}-law"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_app_environment" "env" {
  name                       = "${var.name_prefix}-env"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id
  internal_load_balancer_enabled = true
  infrastructure_subnet_id       = azurerm_subnet.containerapps.id
}

resource "azurerm_servicebus_namespace" "sb" {
  name                = "${var.name_prefix}-sb"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Standard"
  minimum_tls_version = "1.2"
}

resource "azurerm_servicebus_queue" "jobs" {
  name         = var.queue_name
  namespace_id = azurerm_servicebus_namespace.sb.id
  max_delivery_count = 10
  requires_duplicate_detection = true
}

resource "azurerm_storage_account" "sa" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
}

resource "azurerm_storage_container" "artifacts" {
  name                  = "artifacts"
  storage_account_name  = azurerm_storage_account.sa.name
  container_access_type = "private"
}

resource "azurerm_postgresql_flexible_server" "db" {
  name                   = "${var.name_prefix}-pg"
  resource_group_name    = azurerm_resource_group.rg.name
  location               = azurerm_resource_group.rg.location
  administrator_login    = var.db_admin
  administrator_password = var.db_password
  sku_name               = "B_Standard_B1ms"
  storage_mb             = 32768
  version                = "13"
}

resource "azurerm_postgresql_flexible_server_database" "app" {
  name      = "app"
  server_id = azurerm_postgresql_flexible_server.db.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

resource "azurerm_user_assigned_identity" "api" {
  name                = "${var.name_prefix}-api-mi"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_user_assigned_identity" "worker" {
  name                = "${var.name_prefix}-worker-mi"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_container_app" "api" {
  name                         = "${var.name_prefix}-api"
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.api.id]
  }

  ingress {
    external_enabled = true
    target_port      = 8000
  }

  registry { server = var.container_registry }

  template {
    container {
      name   = "api"
      image  = var.api_image
      cpu    = 0.5
      memory = "1.0Gi"
      env {
        name  = "DATABASE_URL"
        value = var.database_url
      }
      env {
        name  = "SERVICE_BUS_CONNECTION"
        secret_name = "sb-conn"
      }
      env {
        name  = "STORAGE_ACCOUNT_URL"
        value = azurerm_storage_account.sa.primary_blob_endpoint
      }
    }
  }
  secret {
    name  = "sb-conn"
    value = azurerm_servicebus_namespace.sb.default_primary_connection_string
  }
}

resource "azurerm_container_app" "worker" {
  name                         = "${var.name_prefix}-worker"
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.worker.id]
  }

  template {
    container {
      name   = "worker"
      image  = var.worker_image
      cpu    = 0.5
      memory = "1.0Gi"
      env {
        name  = "DATABASE_URL"
        value = var.database_url
      }
      env {
        name  = "SERVICE_BUS_CONNECTION"
        secret_name = "sb-conn"
      }
      env {
        name  = "STORAGE_ACCOUNT_URL"
        value = azurerm_storage_account.sa.primary_blob_endpoint
      }
    }
  }
  secret {
    name  = "sb-conn"
    value = azurerm_servicebus_namespace.sb.default_primary_connection_string
  }
}

