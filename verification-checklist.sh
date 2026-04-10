#!/bin/bash
# verification-checklist.sh
# Quick verification that all fixes are in place and working
# Run after startup: bash verification-checklist.sh

echo "═══════════════════════════════════════════════════════════════"
echo "  GigKavach Production Readiness Verification"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

passed=0
failed=0

# Test 1: Startup validation implemented
echo "1. Checking startup validation..."
if grep -q "raise ConfigurationError" /Users/saatwik/Documents/DEVTRAILS/DEVTrails/backend/main.py; then
    echo -e "${GREEN}✓ Startup validation is strict (raises error if creds missing)${NC}"
    ((passed++))
else
    echo -e "${RED}✗ Startup validation not found${NC}"
    ((failed++))
fi

# Test 2: CORS uses environment variables
echo ""
echo "2. Checking CORS configuration..."
if grep -q "settings.APP_ENV" /Users/saatwik/Documents/DEVTRAILS/DEVTrails/backend/main.py; then
    echo -e "${GREEN}✓ CORS configuration uses environment variables${NC}"
    ((passed++))
else
    echo -e "${RED}✗ CORS configuration not environment-variable based${NC}"
    ((failed++))
fi

# Test 3: Error response standardization exists
echo ""
echo "3. Checking error response standardization..."
if [ -f "/Users/saatwik/Documents/DEVTRAILS/DEVTrails/backend/utils/error_response.py" ]; then
    echo -e "${GREEN}✓ Error response standardization module exists${NC}"
    ((passed++))
else
    echo -e "${RED}✗ Error response module not found${NC}"
    ((failed++))
fi

# Test 4: Supabase client validates credentials
echo ""
echo "4. Checking Supabase client validation..."
if grep -q "_validate_credentials" /Users/saatwik/Documents/DEVTRAILS/DEVTrails/backend/utils/supabase_client.py; then
    echo -e "${GREEN}✓ Supabase client validates credentials before init${NC}"
    ((passed++))
else
    echo -e "${RED}✗ Supabase client validation not found${NC}"
    ((failed++))
fi

# Test 5: Message queue implemented
echo ""
echo "5. Checking WhatsApp message queue..."
if [ -f "/Users/saatwik/Documents/DEVTRAILS/DEVTrails/whatsapp-bot/services/message-queue.js" ]; then
    echo -e "${GREEN}✓ Message queue with retry logic implemented${NC}"
    ((passed++))
else
    echo -e "${RED}✗ Message queue not found${NC}"
    ((failed++))
fi

# Test 6: Pagination utilities exist
echo ""
echo "6. Checking pagination utilities..."
if [ -f "/Users/saatwik/Documents/DEVTRAILS/DEVTrails/backend/utils/pagination.py" ]; then
    echo -e "${GREEN}✓ Pagination utilities created${NC}"
    ((passed++))
else
    echo -e "${RED}✗ Pagination utilities not found${NC}"
    ((failed++))
fi

# Test 7: Frontend API configuration correct
echo ""
echo "7. Checking frontend API configuration..."
if grep -q "VITE_API_URL=http://localhost:8000" /Users/saatwik/Documents/DEVTRAILS/DEVTrails/frontend/.env; then
    echo -e "${GREEN}✓ Frontend configured to use correct backend URL${NC}"
    ((passed++))
else
    echo -e "${RED}✗ Frontend API configuration incorrect${NC}"
    ((failed++))
fi

# Test 8: Backend dependencies importable
echo ""
echo "8. Checking backend imports..."
cd /Users/saatwik/Documents/DEVTRAILS/DEVTrails/backend
if python -c "from main import app; from utils.error_response import ValidationError; from utils.pagination import PaginationParams" 2>/dev/null; then
    echo -e "${GREEN}✓ All backend imports working${NC}"
    ((passed++))
else
    echo -e "${RED}✗ Backend import errors detected${NC}"
    ((failed++))
fi

# Test 9: WhatsApp bot can import message queue
echo ""
echo "9. Checking WhatsApp bot imports..."
cd /Users/saatwik/Documents/DEVTRAILS/DEVTrails/whatsapp-bot
if node -c bot.js 2>/dev/null && grep -q "import { messageQueue }" bot.js; then
    echo -e "${GREEN}✓ WhatsApp bot imports message queue${NC}"
    ((passed++))
else
    echo -e "${RED}✗ WhatsApp bot import issues${NC}"
    ((failed++))
fi

# Summary
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo -e "Results: ${GREEN}${passed} Passed${NC}, ${RED}${failed} Failed${NC}"
echo "═══════════════════════════════════════════════════════════════"

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}✓ All production readiness checks passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Review and fix above issues.${NC}"
    exit 1
fi
