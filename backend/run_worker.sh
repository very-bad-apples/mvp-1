#!/bin/bash

# Queue Worker Runner Script
#
# Usage:
#   ./run_worker.sh [worker_id]
#
# Examples:
#   ./run_worker.sh                # Start worker with auto-generated ID
#   ./run_worker.sh worker-1       # Start worker with ID "worker-1"
#
# For multiple workers (horizontal scaling):
#   ./run_worker.sh worker-1 &
#   ./run_worker.sh worker-2 &
#   ./run_worker.sh worker-3 &

# Change to script directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | xargs)
fi

# Run worker with optional worker ID
if [ -z "$1" ]; then
    echo "Starting worker with auto-generated ID..."
    python worker.py
else
    echo "Starting worker with ID: $1"
    python worker.py "$1"
fi
