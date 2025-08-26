#!/bin/bash
# Test Docker build script

set -e  # Exit on error

echo "==================================="
echo "Testing BirdCam Docker Build"
echo "==================================="
echo ""

# Build capture image
echo "1. Building capture image..."
echo "-----------------------------------"
if docker build -f Dockerfile.capture -t birdcam-capture:test .; then
    echo "✅ Capture image built successfully!"
else
    echo "❌ Capture image build failed"
    exit 1
fi

echo ""
echo "2. Building processor image..."
echo "-----------------------------------"
if docker build -f Dockerfile.processor -t birdcam-processor:test .; then
    echo "✅ Processor image built successfully!"
else
    echo "❌ Processor image build failed"
    exit 1
fi

echo ""
echo "3. Checking images..."
echo "-----------------------------------"
docker images | grep birdcam

echo ""
echo "4. Testing docker-compose..."
echo "-----------------------------------"
# Create a basic .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.docker.example .env
    # Set a random secret key
    sed -i "s/your-secret-key-here-change-me/$(openssl rand -hex 32)/" .env
fi

echo "Starting services..."
docker compose up -d

echo ""
echo "5. Checking running containers..."
echo "-----------------------------------"
docker compose ps

echo ""
echo "6. Waiting for services to start (30 seconds)..."
sleep 30

echo ""
echo "7. Checking service health..."
echo "-----------------------------------"
docker compose ps

echo ""
echo "8. Checking logs for errors..."
echo "-----------------------------------"
docker compose logs --tail=20

echo ""
echo "==================================="
echo "Test Summary:"
echo "==================================="
echo "✅ Images built successfully"
echo "✅ Services started"
echo ""
echo "Web UI available at: http://localhost:5001"
echo "Default login: admin / changeme"
echo ""
echo "To stop services: docker compose down"
echo "To view logs: docker compose logs -f"