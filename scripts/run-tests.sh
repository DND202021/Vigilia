#!/bin/bash
# ERIOP Test Runner Script

set -e

echo "=========================================="
echo "  ERIOP Test Suite"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Parse arguments
BACKEND_ONLY=false
FRONTEND_ONLY=false
COVERAGE=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --backend) BACKEND_ONLY=true ;;
        --frontend) FRONTEND_ONLY=true ;;
        --coverage) COVERAGE=true ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Backend tests
if [ "$FRONTEND_ONLY" = false ]; then
    echo -e "\n${YELLOW}Running backend tests...${NC}"
    cd src/backend

    if [ -d ".venv" ]; then
        source .venv/bin/activate
    fi

    if [ "$COVERAGE" = true ]; then
        pytest tests/ -v --cov=app --cov-report=html --cov-report=term
    else
        pytest tests/ -v
    fi

    echo -e "${GREEN}Backend tests passed${NC}"
    cd ../..
fi

# Frontend tests
if [ "$BACKEND_ONLY" = false ]; then
    echo -e "\n${YELLOW}Running frontend tests...${NC}"
    cd src/frontend

    if [ "$COVERAGE" = true ]; then
        npm run test:coverage
    else
        npm run test
    fi

    echo -e "${GREEN}Frontend tests passed${NC}"
    cd ../..
fi

echo -e "\n${GREEN}=========================================="
echo "  All tests passed!"
echo "==========================================${NC}"
