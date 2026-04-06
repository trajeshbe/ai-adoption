# =============================================================================
# Azure Simple Deployment -- Single VM with Docker Compose
#
# Deploys the entire AI Agent Platform on a single Azure VM running
# docker-compose. Suitable for demos, development, and small-scale
# production. Includes auto-TLS via Caddy reverse proxy.
#
# Usage:
#   terraform init
#   terraform apply -var="ssh_public_key=$(cat ~/.ssh/id_ed25519.pub)" \
#                   -var="repo_url=https://github.com/org/repo.git" \
#                   -var="domain=ai.example.com"
# =============================================================================

terraform {
  required_version = ">= 1.5"

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

# -----------------------------------------------------------------------------
# Locals
# -----------------------------------------------------------------------------

locals {
  common_tags = {
    project    = "agent-platform"
    managed-by = "terraform"
    module     = "azure-simple"
  }

  site_domain = var.domain != "" ? var.domain : azurerm_public_ip.main.ip_address
}

# -----------------------------------------------------------------------------
# Resource Group
# -----------------------------------------------------------------------------

resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = local.common_tags
}

# -----------------------------------------------------------------------------
# Networking
# -----------------------------------------------------------------------------

resource "azurerm_virtual_network" "main" {
  name                = "agent-platform-vnet"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  address_space       = ["10.0.0.0/16"]
  tags                = local.common_tags
}

resource "azurerm_subnet" "main" {
  name                 = "agent-platform-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_public_ip" "main" {
  name                = "agent-platform-pip"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = local.common_tags
}

# -----------------------------------------------------------------------------
# Network Security Group
# -----------------------------------------------------------------------------

resource "azurerm_network_security_group" "main" {
  name                = "agent-platform-nsg"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.common_tags

  security_rule {
    name                       = "allow-ssh"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "allow-http"
    priority                   = 200
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "allow-https"
    priority                   = 300
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

# -----------------------------------------------------------------------------
# Network Interface
# -----------------------------------------------------------------------------

resource "azurerm_network_interface" "main" {
  name                = "agent-platform-nic"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.common_tags

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.main.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.main.id
  }
}

resource "azurerm_network_interface_security_group_association" "main" {
  network_interface_id      = azurerm_network_interface.main.id
  network_security_group_id = azurerm_network_security_group.main.id
}

# -----------------------------------------------------------------------------
# Linux Virtual Machine
# -----------------------------------------------------------------------------

resource "azurerm_linux_virtual_machine" "main" {
  name                = "agent-platform-vm"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  size                = var.vm_size
  admin_username      = var.admin_username
  tags                = local.common_tags

  network_interface_ids = [
    azurerm_network_interface.main.id,
  ]

  admin_ssh_key {
    username   = var.admin_username
    public_key = var.ssh_public_key
  }

  os_disk {
    name                 = "agent-platform-osdisk"
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = var.disk_size
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  custom_data = base64encode(templatefile("${path.module}/cloud-init.yaml", {
    repo_url    = var.repo_url
    site_domain = var.domain
    public_ip   = azurerm_public_ip.main.ip_address
  }))

  lifecycle {
    ignore_changes = [custom_data]
  }
}

# -----------------------------------------------------------------------------
# Cloud-Init Template (inline, rendered as custom_data)
#
# We use a templatefile for the cloud-init YAML. The file is created below
# as a local_file so the module is self-contained.
# -----------------------------------------------------------------------------

resource "local_file" "cloud_init" {
  filename = "${path.module}/cloud-init.yaml"
  content  = <<-YAML
    #cloud-config
    package_update: true
    package_upgrade: true

    packages:
      - apt-transport-https
      - ca-certificates
      - curl
      - gnupg
      - lsb-release
      - git
      - jq

    runcmd:
      # Install Docker
      - curl -fsSL https://get.docker.com | sh
      - systemctl enable docker
      - systemctl start docker

      # Install Docker Compose plugin
      - mkdir -p /usr/local/lib/docker/cli-plugins
      - curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)" -o /usr/local/lib/docker/cli-plugins/docker-compose
      - chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

      # Clone repository
      - git clone ${repo_url} /opt/agent-platform
      - cd /opt/agent-platform

      # Write environment file
      - |
        cat > /opt/agent-platform/.env <<'ENVEOF'
        SITE_DOMAIN=${site_domain != "" ? site_domain : public_ip}
        NEXT_PUBLIC_GRAPHQL_URL=${site_domain != "" ? "https://${site_domain}/graphql" : "http://${public_ip}/graphql"}
        POSTGRES_PASSWORD=agent_platform
        ENVEOF

      # Start the platform (CPU-only + web profile for Caddy reverse proxy)
      - cd /opt/agent-platform && docker compose -f docker-compose.yml -f docker-compose.cpu.yml --profile web up -d --build

    final_message: "AI Agent Platform deployment complete after $UPTIME seconds"
  YAML

  lifecycle {
    ignore_changes = [content]
  }
}
