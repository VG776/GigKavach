#!/usr/bin/env bash
# ═════════════════════════════════════════════════════════════════
# GigKavach WhatsApp Bot Install Script
# Fixes Puppeteer download issues and installs dependencies
# ═════════════════════════════════════════════════════════════════

set -e

echo "🤖 GigKavach WhatsApp Bot Setup"
echo "════════════════════════════════════════════════════════════"

# Step 1: Clean up any existing node_modules and npm cache
echo ""
echo "Step 1: Cleaning up..."
rm -rf node_modules package-lock.json 2>/dev/null || true

# Step 2: Install dependencies with Puppeteer download skipped
echo ""
echo "Step 2: Installing dependencies..."
PUPPETEER_SKIP_DOWNLOAD=true npm install

# Step 3: Create data directory for session storage
echo ""
echo "Step 3: Creating data directories..."
mkdir -p data/sessions

# Step 4: Create .env if it doesn't exist
if [ ! -f .env ]; then
  echo ""
  echo "Step 4: Creating .env file..."
  cp .env.example .env
  echo "✅ .env created from .env.example"
else
  echo "✅ .env already exists"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Scan the QR code with WhatsApp: npm start"
echo "  2. Keep the bot running: node bot.js"
echo ""
echo "For help: npm run dev (with auto-reload on file changes)"
echo "════════════════════════════════════════════════════════════"
