output "container_app_api_url" {
  value = azurerm_container_app.api.latest_revision_fqdn
}

output "servicebus_connection" {
  value     = azurerm_servicebus_namespace.sb.default_primary_connection_string
  sensitive = true
}

output "storage_account" {
  value = azurerm_storage_account.sa.name
}
