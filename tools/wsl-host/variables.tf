variable "location" {
  description = "Azure region. Defaults to pycloudlib's default so resources land next to the other test VMs."
  type        = string
  default     = "centralus"
}

variable "vm_size" {
  description = "VM size. Must support nested virtualization (WSL 2 needs Hyper-V)."
  type        = string
  default     = "Standard_D4s_v5"
}

variable "image_sku" {
  description = "Windows 11 marketplace SKU under offer 'windows-11'."
  type        = string
  default     = "win11-24h2-pro"
}

variable "ssh_source_address_prefix" {
  description = "CIDR (or '*') allowed to reach port 22. Password auth is disabled, so '*' is key-only."
  type        = string
  default     = "*"
}

variable "admin_password" {
  description = "Admin password for the 'ubuntu' account. Generated when unset. Also used for automatic logon, which winget needs."
  type        = string
  default     = null
  sensitive   = true
}

variable "wsl_msi_url" {
  description = "WSL installer to use. 'latest' resolves the newest stable GitHub release; 'prerelease' the newest pre-release; anything else is taken as a direct .msi URL."
  type        = string
  default     = "latest"
}

variable "ready_timeout_minutes" {
  description = "How long to wait after the reboot for the host to report ready."
  type        = number
  default     = 25
}

variable "tags" {
  description = "Extra tags applied to every resource."
  type        = map(string)
  default     = {}
}
