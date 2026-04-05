#!/bin/bash

# GigKavach Multi-Service Startup
# Supports both localhost and server IP (13.51.165.52) deployments
# Works with tmux on server
# Usage: ./startup_suite.sh [local|server]

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track PIDs for cleanup
BACKEND_PID=""
FRONTEND_PID=""
PROJECT_ROOT=""

# Cleanup function - runs on Ctrl+C or script exit
cleanup() {
  echo -e "\n${YELLOW}Shutting down all services...${NC}"
  [ -n "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null || true
  wait 2>/dev/null || true
  echo -e "${GREEN}✅ All services stopped${NC}"
  exit 0
}

# Set trap to call cleanup on Ctrl+C and normal exit
trap cleanup SIGINT SIGTERM EXIT

set -e  # Exit on any error during setup

# Determine deployment mode
MODE="${1:-local}"

if [[ "$MODE" != "local" && "$MODE" != "server" ]]; then
  echo "Usage: ./startup_suite.sh [local|server]"
  echo "  local  - Run on http://localhost (development)"
  echo "  server - Run on http://13.51.165.52 (production)"
  exit 1
fi

if [[ "$MODE" == "local" ]]; then
  API_HOST="localhost"
  API_URL="http://localhost:8000"
  BOT_URL="http://localhost:3001"
  FRONTEND_URL="http://localhost:3000"
else
  API_HOST="13.51.165.52"
  API_URL="http://13.51.165.52:8000"
  BOT_URL="http://13.51.165.52:3001"
  FRONTEND_URL="http://13.51.165.52:3000"
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🚀 Starting GigKavach Services ($MODE mode)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}📍 API:${NC}      $API_URL"
echo -e "${BLUE}📍 Bot:${NC}      $BOT_URL"
echo -e "${BLUE}📍 Frontend:${NC} $FRONTEND_URL"
echo ""

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Kill old processes if they exist
echo -e "${YELLOW}🧹 Cleaning up old processes...${NC}"
pkill -f "uvicorn main:app" > /dev/null 2>&1 || true
pkill -f "vite" > /dev/null 2>&1 || true
pkill -f "node bot.js" > /dev/null 2>&1 || true
sleep 1

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/backend/logs"

# Update frontend .env
cat > "$PROJECT_ROOT/frontend/.env" << 'EOF'
VITE_SUPABASE_URL=https://rwzjpuxyaxjymhjkpxrm.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ3empwdXh5YXhqeW1oamtweHJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQyNjU2MzEsImV4cCI6MjA4OTg0MTYzMX0.t51gBkCcxvFG47PRGoBd4rOp1swaTxFCbZLNl_qeAr4
EOF

cat >> "$PROJECT_ROOT/frontend/.env" << EOF
VITE_API_URL=$API_URL
VITE_API_BASE_URL=$API_URL
VITE_WS_BASE_URL=ws://$API_HOST:8000
VITE_ENABLE_MOCK_DATA=false
VITE_DEBUG_MODE=false
EOF

# Update backend .env
cat > "$PROJECT_ROOT/backend/.env" << 'EOF'
APP_ENV=development
APP_SECRET_KEY=your-secret-key-here
FRONTEND_LOCAL_URL=http://localhost:3000
FRONTEND_SERVER_URL=http://13.51.165.52:3000
FRONTEND_URL=http://13.51.165.52:3000
FRONTEND_PRODUCTION_URL=https://gigkavach-delta.vercel.app
SUPABASE_URL=https://rwzjpuxyaxjymhjkpxrm.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ3empwdXh5YXhqeW1oamtweHJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQyNjU2MzEsImV4cCI6MjA4OTg0MTYzMX0.t51gBkCcxvFG47PRGoBd4rOp1swaTxFCbZLNl_qeAr4
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ3empwdXh5YXhqeW1oamtweHJtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NDI2NTYzMSwiZXhwIjoyMDg5ODQxNjMxfQ.eoo61p_aP4VH0wRixdGrki_6LZjJw2WBVYXLydgqFxQ
REDIS_URL=redis://localhost:6379/0
TOMORROW_IO_API_KEY=MD36I2GcYp3gBoUlnKvdQeHkBJQvTF19
OPENAQ_API_KEY=885d52c7b9d35c87345de923622c6481fb5be3ec1b2a57952956cd5c386c2f0b
AQICN_API_TOKEN=ca8e43f08a82415e64b9d84111785b2bf7e8db70
DCI_POLL_INTERVAL_SECONDS=300
DCI_TRIGGER_THRESHOLD=65
DCI_CATASTROPHIC_THRESHOLD=85
DCI_CACHE_TTL_SECONDS=1800
FRAUD_SOFT_FLAG_SIGNALS=3
FRAUD_HARD_BLOCK_SIGNALS=5
FRAUD_CONTAMINATION_RATE=0.05
COVERAGE_DELAY_HOURS=24
MAX_UPI_RETRY_ATTEMPTS=3
UPI_RETRY_INTERVAL_MINUTES=40
ESCROW_WINDOW_HOURS=48
SHIELD_BASIC_PREMIUM=69
SHIELD_PLUS_PREMIUM=89
SHIELD_PRO_PREMIUM=99
SHIELD_BASIC_COVERAGE_PCT=0.40
SHIELD_PLUS_COVERAGE_PCT=0.50
SHIELD_PRO_COVERAGE_PCT=0.70
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
MAPPLS_API_KEY=your-mappls-key-here
WHATSAPP_PHONE_NUMBER=8792525542
EOF

# Update whatsapp-bot .env
cat > "$PROJECT_ROOT/whatsapp-bot/.env" << EOF
BACKEND_URL=$API_URL
BOT_PORT=3001
DEBUG=false
LOG_LEVEL=info
SESSION_DIR=./sessions
WHATSAPP_PHONE_NUMBER=8792525542
EOF

echo -e "${GREEN}✅ Environment files configured for $MODE mode${NC}"
echo ""

# ══════════════════════════════════════════════════════════════════════════════
# START BACKEND
# ══════════════════════════════════════════════════════════════════════════════
echo -e "${YELLOW}🐍 Starting Backend (port 8000)...${NC}"
cd "$PROJECT_ROOT/backend"

# Ensure venv exists
if [ ! -d ".venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv .venv
fi

# Install/upgrade dependencies
.venv/bin/pip install -q -r requirements.txt

# Start backend using absolute path (bypasses venv activation issues)
nohup .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload > backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 4

# Verify backend started
if ps -p $BACKEND_PID > /dev/null 2>&1; then
  echo -e "${GREEN}✅ Backend started (PID: $BACKEND_PID)${NC}"
else
  echo -e "${RED}❌ Backend failed to start${NC}"
  echo -e "${RED}Error log:${NC}"
  tail -30 backend.log
  cd "$PROJECT_ROOT"
  exit 1
fi
cd "$PROJECT_ROOT"

# ══════════════════════════════════════════════════════════════════════════════
# START FRONTEND
# ══════════════════════════════════════════════════════════════════════════════
echo -e "${YELLOW}🎨 Starting Frontend (port 3000)...${NC}"
cd "$PROJECT_ROOT/frontend"

# Ensure dependencies are installed
if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm install --legacy-peer-deps || {
    echo -e "${RED}❌ npm install failed${NC}"
    cd "$PROJECT_ROOT"
    exit 1
  }
fi

nohup npm run dev -- --host 0.0.0.0 --port 3000 > frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to start
echo "Waiting for frontend to start..."
sleep 4

# Verify frontend started
if ps -p $FRONTEND_PID > /dev/null 2>&1; then
  echo -e "${GREEN}✅ Frontend started (PID: $FRONTEND_PID)${NC}"
else
  echo -e "${RED}❌ Frontend failed to start${NC}"
  echo -e "${RED}Error log:${NC}"
  tail -30 frontend.log
  cd "$PROJECT_ROOT"
  exit 1
fi
cd "$PROJECT_ROOT"

# ══════════════════════════════════════════════════════════════════════════════
# START WHATSAPP BOT
# ══════════════════════════════════════════════════════════════════════════════
echo -e "${YELLOW}💬 Starting WhatsApp Bot (port 3001)...${NC}"
cd "$PROJECT_ROOT/whatsapp-bot"

# Ensure dependencies are installed
if [ ! -d "node_modules" ]; then
  echo "Installing bot dependencies..."
  npm install --legacy-peer-deps || {
    echo -e "${RED}❌ npm install failed${NC}"
    exit 1
  }
fi

# Create sessions directory
mkdir -p sessions

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 All services started successfully!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Service URLs:${NC}"
echo -e "  Frontend:  ${BLUE}$FRONTEND_URL${NC}"
echo -e "  Backend:   ${BLUE}$API_URL/docs${NC}"
echo -e "  WhatsApp:  ${BLUE}$BOT_URL/health${NC}"
echo ""
echo -e "${YELLOW}Background Logs:${NC}"
echo -e "  Backend:   ${BLUE}$PROJECT_ROOT/backend/backend.log${NC}"
echo -e "  Frontend:  ${BLUE}$PROJECT_ROOT/frontend/frontend.log${NC}"
echo ""
echo -e "${YELLOW}Running processes:${NC}"
echo -e "  Backend:   ${BLUE}PID $BACKEND_PID${NC}"
echo -e "  Frontend:  ${BLUE}PID $FRONTEND_PID${NC}"
echo ""
echo -e "${YELLOW}📱 WhatsApp Bot starting in foreground...${NC}"
echo -e "${YELLOW}Scan the QR code with WhatsApp on your phone.${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all services.${NC}"
echo ""

# Run WhatsApp bot in FOREGROUND so user sees QR code
# This keeps the script alive and interactive
node bot.js

# When bot exits (Ctrl+C), kill all background processes
echo -e "${YELLOW}Shutting down all services...${NC}"
kill $BACKEND_PID 2>/dev/null || true
kill $FRONTEND_PID 2>/dev/null || true
wait
echo -e "${GREEN}✅ All services stopped${NC}"
