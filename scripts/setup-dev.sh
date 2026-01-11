#!/bin/bash
# ERIOP Development Environment Setup Script

set -e

echo "=========================================="
echo "  ERIOP Development Setup"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

command -v docker >/dev/null 2>&1 || { echo -e "${RED}Docker is required but not installed.${NC}" >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || command -v "docker compose" >/dev/null 2>&1 || { echo -e "${RED}Docker Compose is required but not installed.${NC}" >&2; exit 1; }

echo -e "${GREEN}Prerequisites OK${NC}"

# Create environment files if they don't exist
echo -e "\n${YELLOW}Setting up environment files...${NC}"

if [ ! -f "src/backend/.env" ]; then
    cp src/backend/.env.example src/backend/.env
    echo -e "${GREEN}Created src/backend/.env${NC}"
else
    echo "src/backend/.env already exists"
fi

# Start infrastructure services
echo -e "\n${YELLOW}Starting infrastructure services...${NC}"
docker compose up -d postgres timescaledb redis mosquitto

# Wait for services to be healthy
echo -e "\n${YELLOW}Waiting for services to be ready...${NC}"
sleep 5

# Backend setup
echo -e "\n${YELLOW}Setting up backend...${NC}"
cd src/backend

if command -v python3.11 &> /dev/null; then
    PYTHON=python3.11
elif command -v python3 &> /dev/null; then
    PYTHON=python3
else
    PYTHON=python
fi

if [ ! -d ".venv" ]; then
    $PYTHON -m venv .venv
    echo -e "${GREEN}Created virtual environment${NC}"
fi

source .venv/bin/activate
pip install -e ".[dev]" --quiet
echo -e "${GREEN}Backend dependencies installed${NC}"

cd ../..

# Frontend setup
echo -e "\n${YELLOW}Setting up frontend...${NC}"
cd src/frontend

if command -v npm &> /dev/null; then
    npm install --silent
    echo -e "${GREEN}Frontend dependencies installed${NC}"
else
    echo -e "${YELLOW}npm not found, skipping frontend setup${NC}"
fi

cd ../..

echo -e "\n${GREEN}=========================================="
echo "  Setup Complete!"
echo "==========================================${NC}"
echo ""
echo "To start development:"
echo "  Backend:  cd src/backend && source .venv/bin/activate && uvicorn app.main:app --reload"
echo "  Frontend: cd src/frontend && npm run dev"
echo ""
echo "Or use Docker:"
echo "  docker compose up"
echo ""
echo "API will be available at: http://localhost:8000"
echo "Frontend will be available at: http://localhost:3000"
