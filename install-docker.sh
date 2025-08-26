#!/bin/bash
# Docker installation script for Ubuntu 24.04

echo "Installing Docker on Ubuntu 24.04..."
echo "This script requires sudo access."
echo ""

# Update package index
echo "Step 1: Updating package index..."
sudo apt-get update

# Install prerequisites
echo "Step 2: Installing prerequisites..."
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
echo "Step 3: Adding Docker GPG key..."
sudo mkdir -m 0755 -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up the repository
echo "Step 4: Setting up Docker repository..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package index again
echo "Step 5: Updating package index with Docker repo..."
sudo apt-get update

# Install Docker Engine
echo "Step 6: Installing Docker Engine, CLI, and plugins..."
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add current user to docker group (to run without sudo)
echo "Step 7: Adding $USER to docker group..."
sudo usermod -aG docker $USER

# Start and enable Docker
echo "Step 8: Starting Docker service..."
sudo systemctl start docker
sudo systemctl enable docker

# Test Docker installation
echo "Step 9: Testing Docker installation..."
sudo docker run hello-world

echo ""
echo "✅ Docker installation complete!"
echo ""
echo "⚠️  IMPORTANT: You need to log out and back in for group changes to take effect."
echo "   Or run: newgrp docker"
echo ""
echo "To verify installation after re-login:"
echo "  docker --version"
echo "  docker compose version"
echo "  docker run hello-world"