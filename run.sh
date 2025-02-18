#!/bin/bash

echo "Moon Monitor - Setup and Launch Script"
echo "====================================="
echo

# Check for Python 3.11 installation
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3 &> /dev/null; then
    PY_VERSION=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    if [[ $(echo "$PY_VERSION >= 3.11 && $PY_VERSION < 3.12" | bc -l) == 1 ]]; then
        PYTHON_CMD="python3"
    else
        echo "Error: Python 3.11 is required but not found"
        echo "Current Python version: $PY_VERSION"
        echo "Please install Python 3.11 from https://www.python.org/"
        exit 1
    fi
else
    echo "Error: Python is not installed"
    echo "Please install Python 3.11 from https://www.python.org/"
    exit 1
fi

# Check for Node.js installation
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed"
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi

# Create necessary directories
if [ ! -d "backend/secure" ]; then
    echo "Creating secure directory..."
    mkdir -p "backend/secure"
fi

# Create Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    $PYTHON_CMD -m venv venv
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment and install requirements
echo "Installing Python dependencies..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "Error: Failed to activate virtual environment"
    exit 1
fi

# Ensure pip is up to date
python -m pip install --upgrade pip

# Install specific versions of critical packages first
pip install "fastapi<0.100.0" "pydantic<2.0.0" uvicorn
if [ $? -ne 0 ]; then
    echo "Error: Failed to install critical dependencies"
    exit 1
fi

# Install remaining requirements
pip install -r backend/requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install Python dependencies"
    exit 1
fi

# Install frontend dependencies if node_modules doesn't exist
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd frontend
    npm install
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install frontend dependencies"
        cd ..
        exit 1
    fi
    cd ..
fi

echo
echo "Setup completed successfully!"
echo
echo "Starting services..."
echo

# Create a default settings file if it doesn't exist
if [ ! -f "backend/secure/settings.json" ]; then
    echo "Creating default settings file..."
    echo '{"slippage": 5, "priority_fee": 0.005}' > backend/secure/settings.json
fi

# Create a default wallets file if it doesn't exist
if [ ! -f "backend/secure/wallets.json" ]; then
    echo "Creating default wallets file..."
    echo '{"wallets": []}' > backend/secure/wallets.json
fi

# Function to cleanup background processes on script exit
cleanup() {
    echo
    echo "Shutting down services..."
    kill $(jobs -p) 2>/dev/null
    exit
}

# Set up trap to catch script termination
trap cleanup EXIT INT TERM

# Start backend server
echo "Starting backend server..."
(source venv/bin/activate && cd backend && uvicorn main:app --reload) &

# Start frontend server
echo "Starting frontend server..."
(cd frontend && npm run dev) &

echo
echo "Moon Monitor is starting..."
echo
echo "Access the application at:"
echo "Frontend: http://localhost:5173"
echo "Backend:  http://localhost:8000"
echo
echo "Press Ctrl+C to stop all services."
echo

# Wait for user interrupt
wait 