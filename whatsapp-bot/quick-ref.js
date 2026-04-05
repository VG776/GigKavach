#!/usr/bin/env node

/**
 * Quick reference for common operations
 */

console.log(`
╔══════════════════════════════════════════════════════════════════╗
║                GigKavach WhatsApp Bot v2.0                        ║
║                    Quick Reference Card                           ║
╚══════════════════════════════════════════════════════════════════╝

🚀 QUICK START
──────────────────────────────────────────────────────────────────
  cd whatsapp-bot
  chmod +x install.sh
  ./install.sh
  npm start


💬 WORKER COMMANDS (via WhatsApp)
──────────────────────────────────────────────────────────────────
  JOIN    - Start registration (4 minutes)
  STATUS  - Check coverage & DCI score
  SHIFT   - Update working hours
  RENEW   - Renew weekly protection
  LANG    - Change language (5 options)
  APPEAL  - Contest fraudulent decision
  HELP    - Show all commands


🔌 BACKEND API (REST Endpoints)
──────────────────────────────────────────────────────────────────
  POST /send-message
       → Send message to single worker

  POST /broadcast-disruption-alert
       → Broadcast alert to multiple workers

  POST /send-payout-confirmation
       → Send payout confirmation

  POST /send-fraud-alert
       → Send fraud alert (soft/hard/blacklist)

  GET /health
       → Check bot connection status

  GET /stats
       → View session statistics


📋 ENVIRONMENT (.env file)
──────────────────────────────────────────────────────────────────
  BOT_PORT=3001
  BACKEND_URL=http://localhost:8000
  DEBUG=false


🐛 Fix Common Issues
──────────────────────────────────────────────────────────────────
  Port in use:          lsof -i :3001 | kill -9 Process
  QR not showing:       rm -rf data/sessions/* && npm start
  npm install errors:   PUPPETEER_SKIP_DOWNLOAD=true npm install
  Session lost:         Sessions auto-save in data/sessions/


📊 Monitoring
──────────────────────────────────────────────────────────────────
  curl http://localhost:3001/health
  curl http://localhost:3001/stats


📚 Documentation
──────────────────────────────────────────────────────────────────
  README.md        - Complete API reference
  SETUP_GUIDE.md   - Detailed setup & deployment guide
  .env.example     - Environment configuration


🚀 Deployment
──────────────────────────────────────────────────────────────────
  AWS EC2:         Follow SETUP_GUIDE.md § AWS EC2
  Render.com:      Follow SETUP_GUIDE.md § Render.com
  Docker:          Follow SETUP_GUIDE.md § Docker


✅ TECH STACK
──────────────────────────────────────────────────────────────────
  Runtime:         Node.js v16+
  WhatsApp:        whatsapp-web.js v1.23
  API Server:      Express.js v4.18
  Session Store:   File-based JSON
  Auth:            LocalAuth (whatsapp-web.js)


📦 For Help
──────────────────────────────────────────────────────────────────
  1. Check README.md troubleshooting section
  2. Review SETUP_GUIDE.md
  3. Check bot logs: npm start 2>&1 | tee bot.log


Built by Team Quadcore 🛡️  |  GigKavach v2.0
════════════════════════════════════════════════════════════════════
`);
