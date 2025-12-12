variable "name_prefix" { type = string }
variable "location" { type = string default = "eastus" }
variable "resource_group" { type = string }
variable "queue_name" { type = string default = "jobs" }
variable "storage_account_name" { type = string }
variable "db_admin" { type = string }
variable "db_password" { type = string sensitive = true }
variable "api_image" { type = string }
variable "worker_image" { type = string }
variable "container_registry" { type = string }
variable "database_url" { type = string }
