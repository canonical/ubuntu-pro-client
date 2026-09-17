# Windows 11 host for running the behave suite against WSL.
#
# `terraform apply` leaves a host the behave harness can use immediately:
#
#   1. network + VM                   (azurerm)
#   2. bootstrap.ps1 as SYSTEM        (run command: sshd, WSL, winget, autologon)
#   3. reboot                         (azapi restart action; WSL features need it)
#   4. wait-ready.ps1 as SYSTEM       (run command: blocks until the post-logon
#                                      task has verified winget and WSL work)
#
# The `behave_env` output holds the environment the harness needs.

locals {
  # The harness hard-codes this account: it pushes files to
  # C:\Users\ubuntu\... and runs `wsl` as the SSH login user.
  admin_username = "ubuntu"

  admin_password = coalesce(var.admin_password, one(random_password.admin[*].result))

  ssh_dir              = "${path.module}/.ssh"
  ssh_private_key_path = "${local.ssh_dir}/${var.name}"
  ssh_public_key_path  = "${local.ssh_dir}/${var.name}.pub"

  tags = merge(
    {
      name       = var.name
      created_by = "ubuntu-pro-client/tools/wsl-host"
    },
    var.tags,
  )
}

# --- Secrets ------------------------------------------------------------------

resource "random_password" "admin" {
  count = var.admin_password == null ? 1 : 0

  # Windows complexity rules: >= 12 chars, 3 of 4 character classes.
  length           = 24
  min_upper        = 2
  min_lower        = 2
  min_numeric      = 2
  min_special      = 2
  override_special = "!@#%^*-_=+"
}

resource "tls_private_key" "ssh" {
  algorithm = "ED25519"
}

resource "local_sensitive_file" "ssh_private_key" {
  filename        = local.ssh_private_key_path
  content         = tls_private_key.ssh.private_key_openssh
  file_permission = "0600"
}

resource "local_file" "ssh_public_key" {
  filename        = local.ssh_public_key_path
  content         = "${trimspace(tls_private_key.ssh.public_key_openssh)} ${var.name}\n"
  file_permission = "0644"
}

# --- Network ------------------------------------------------------------------

resource "azurerm_resource_group" "wsl" {
  name     = "${var.name}-rg"
  location = var.location
  tags     = local.tags
}

resource "azurerm_virtual_network" "wsl" {
  name                = "${var.name}-vnet"
  location            = azurerm_resource_group.wsl.location
  resource_group_name = azurerm_resource_group.wsl.name
  address_space       = ["10.0.0.0/16"]
  tags                = local.tags
}

resource "azurerm_subnet" "wsl" {
  name                 = "${var.name}-subnet"
  resource_group_name  = azurerm_resource_group.wsl.name
  virtual_network_name = azurerm_virtual_network.wsl.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_public_ip" "wsl" {
  name                = "${var.name}-ip"
  location            = azurerm_resource_group.wsl.location
  resource_group_name = azurerm_resource_group.wsl.name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = local.tags
}

resource "azurerm_network_security_group" "wsl" {
  name                = "${var.name}-nsg"
  location            = azurerm_resource_group.wsl.location
  resource_group_name = azurerm_resource_group.wsl.name
  tags                = local.tags

  security_rule {
    name                       = "ssh"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = var.ssh_source_address_prefix
    destination_address_prefix = "*"
  }
}

resource "azurerm_network_interface" "wsl" {
  name                = "${var.name}-nic"
  location            = azurerm_resource_group.wsl.location
  resource_group_name = azurerm_resource_group.wsl.name
  tags                = local.tags

  ip_configuration {
    name                          = "primary"
    subnet_id                     = azurerm_subnet.wsl.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.wsl.id
  }
}

resource "azurerm_network_interface_security_group_association" "wsl" {
  network_interface_id      = azurerm_network_interface.wsl.id
  network_security_group_id = azurerm_network_security_group.wsl.id
}

# --- VM -----------------------------------------------------------------------

resource "azurerm_windows_virtual_machine" "wsl" {
  name                = var.name
  computer_name       = var.name
  location            = azurerm_resource_group.wsl.location
  resource_group_name = azurerm_resource_group.wsl.name
  size                = var.vm_size
  admin_username      = local.admin_username
  admin_password      = local.admin_password
  tags                = local.tags

  network_interface_ids = [azurerm_network_interface.wsl.id]

  # Windows 11 on Azure needs multitenant hosting rights.
  license_type = "Windows_Client"

  # Skip any automatic reboots
  patch_mode                   = "Manual"
  automatic_updates_enabled    = false

  # Trusted Launch (secure boot / vTPM) does not support nested virtualization,
  # which WSL 2 requires.
  secure_boot_enabled = false
  vtpm_enabled        = false

  source_image_reference {
    publisher = "MicrosoftWindowsDesktop"
    offer     = "windows-11"
    sku       = var.image_sku
    version   = "latest"
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = 128
  }

  boot_diagnostics {}
}

# --- Post-provisioning --------------------------------------------------------

resource "azurerm_virtual_machine_run_command" "bootstrap" {
  name               = "bootstrap"
  location           = azurerm_resource_group.wsl.location
  virtual_machine_id = azurerm_windows_virtual_machine.wsl.id
  tags               = local.tags

  source {
    script = file("${path.module}/bootstrap.ps1")
  }

  # Values are base64-encoded so spaces and shell metacharacters survive the
  # run-command handler's argument quoting.
  parameter {
    name  = "AdminUser"
    value = local.admin_username
  }
  parameter {
    name  = "SshPublicKeyB64"
    value = base64encode(local_file.ssh_public_key.content)
  }
  parameter {
    name  = "WslMsiSpec"
    value = var.wsl_msi_url
  }
  protected_parameter {
    name  = "AdminPasswordB64"
    value = base64encode(local.admin_password)
  }

  timeouts {
    create = "45m"
  }

  lifecycle {
    postcondition {
      condition     = self.instance_view[0].exit_code == 0
      error_message = "bootstrap.ps1 failed (exit ${self.instance_view[0].exit_code}): ${self.instance_view[0].error_message}"
    }
  }
}

resource "azapi_resource_action" "reboot" {
  type        = "Microsoft.Compute/virtualMachines@2024-07-01"
  resource_id = azurerm_windows_virtual_machine.wsl.id
  action      = "restart"
  method      = "POST"

  depends_on = [azurerm_virtual_machine_run_command.bootstrap]
}

resource "azurerm_virtual_machine_run_command" "wait_ready" {
  name               = "wait-ready"
  location           = azurerm_resource_group.wsl.location
  virtual_machine_id = azurerm_windows_virtual_machine.wsl.id
  tags               = local.tags

  source {
    script = file("${path.module}/wait-ready.ps1")
  }

  parameter {
    name  = "TimeoutMinutes"
    value = tostring(var.ready_timeout_minutes)
  }

  timeouts {
    create = "${var.ready_timeout_minutes + 15}m"
  }

  lifecycle {
    postcondition {
      condition     = self.instance_view[0].exit_code == 0
      error_message = "Host did not become ready (exit ${self.instance_view[0].exit_code}): ${self.instance_view[0].error_message}"
    }
  }

  depends_on = [azapi_resource_action.reboot]
}
