output "ip_address" {
  description = "Public IP of the Windows host."
  value       = azurerm_public_ip.wsl.ip_address
}

output "ssh_private_key_path" {
  value = abspath(local_sensitive_file.ssh_private_key.filename)
}

output "ssh_public_key_path" {
  value = abspath(local_file.ssh_public_key.filename)
}

output "behave_env" {
  description = "Environment the behave harness needs. Use: eval \"$(terraform output -raw behave_env)\""
  value       = <<-EOT
    export UACLIENT_BEHAVE_WSL_IP_ADDRESS=${azurerm_public_ip.wsl.ip_address}
    export UACLIENT_BEHAVE_WSL_PRIVKEY_PATH=${abspath(local_sensitive_file.ssh_private_key.filename)}
    export UACLIENT_BEHAVE_WSL_PUBKEY_PATH=${abspath(local_file.ssh_public_key.filename)}
  EOT
}

output "ssh_command" {
  description = "Interactive shell on the Windows host."
  value       = "ssh -i ${abspath(local_sensitive_file.ssh_private_key.filename)} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${local.admin_username}@${azurerm_public_ip.wsl.ip_address}"
}

output "admin_password" {
  description = "Only needed for interactive debugging (RDP/Bastion). SSH is key-only."
  value       = local.admin_password
  sensitive   = true
}
