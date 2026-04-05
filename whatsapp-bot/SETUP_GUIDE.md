# GigKavach WhatsApp Bot — Complete Setup Guide

## 🎯 Overview

This guide walks you through setting up and running the **GigKavach WhatsApp Bot v2.0**, which handles:
- ✅ Worker onboarding via WhatsApp (4 minutes, 5 languages)
- ✅ Disruption alerts when DCI ≥ 65
- ✅ Payout confirmations (zero-touch payments)
- ✅ Session persistence (QR scan once, auto-reconnect forever)
- ✅ REST API for backend integration

---

## 📦 Installation

### Quick Install (Automated)

```bash
cd /path/to/whatsapp-bot
chmod +x install.sh
./install.sh
```

This script automatically:
1. ✅ Cleans up old node_modules
2. ✅ Installs dependencies (Puppeteer download skipped)
3. ✅ Creates `data/` directory for session storage
4. ✅ Sets up `.env` file

### Manual Install (If script fails)

**macOS/Linux:**
```bash
cd whatsapp-bot
rm -rf node_modules package-lock.json
PUPPETEER_SKIP_DOWNLOAD=true npm install
mkdir -p data/sessions
cp .env.example .env
```

**Windows (PowerShell):**
```powershell
cd whatsapp-bot
rmdir /s /q node_modules
$env:PUPPETEER_SKIP_DOWNLOAD="true"; npm install
mkdir data/sessions
copy .env.example .env
```

---

## 🚀 Starting the Bot

### First Run (QR Code Authentication)

```bash
npm start
```

**Output:**
```
ℹ️  🤖 Initializing GigKavach WhatsApp Bot...
⚠️  📱 SCAN THIS QR CODE WITH YOUR WHATSAPP TO LOGIN
(Session will be saved for future auto-login)

████████████████████████████████████████
████ ▄▄▄▄▄ █▀█▀▀█▄ ▄▄▄▄▄ ████████████
████ █   █ █▄▀▄█▄ █   █ ████████████
...

✅ WhatsApp bot is ready and listening for messages!
ℹ️  Backend URL: http://localhost:8000
ℹ️  Bot API listening on port 3001
Available endpoints:
  POST   /send-message
  POST   /broadcast-disruption-alert
  POST   /send-payout-confirmation
  POST   /send-fraud-alert
  GET    /health
  GET    /stats

Starting WhatsApp client...
```

**What to do:**
1. Open WhatsApp on your phone
2. Go to **Settings** → **Linked Devices** → **Link a Device**
3. Point camera at the QR code in the terminal
4. ✅ Connected!

### Subsequent Runs (Auto-Connect)

After the first run, the bot automatically reconnects:
```bash
npm start

# Session detected from ./data/sessions/
# Connecting to WhatsApp...
✅ WhatsApp bot is ready and listening for messages!
🌐 Listening on http://localhost:3001
```

**No QR code needed!**

---

## 🔧 Configuration

### .env File

Copy from `.env.example` and edit:

```env
# Bot API Server Port
BOT_PORT=3001

# Backend API URL (where worker registration lives)
BACKEND_URL=http://localhost:8000

# Logging
DEBUG=false
```

---

## 💬 Testing the Bot

### Send a Test Message

```bash
curl -X POST http://localhost:3001/send-message \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "919876543210",
    "message": "Hello from GigKavach! 🛡️",
    "messageType": "test"
  }'
```

**Response:**
```json
{
  "status": "success",
  "phone": "919876543210",
  "messageType": "test",
  "timestamp": "2026-04-04T10:30:00Z"
}
```

### Health Check

```bash
curl http://localhost:3001/health

# Returns:
{
  "status": "ok",
  "bot_name": "GigKavach WhatsApp Bot v2.0",
  "connected": true,
  "timestamp": "2026-04-04T10:30:00Z",
  "uptime_seconds": 120
}
```

### View Bot Statistics

```bash
curl http://localhost:3001/stats

# Returns:
{
  "status": "ok",
  "total_sessions": 5,
  "active_sessions": 3,
  "uptime_seconds": 450,
  "timestamp": "2026-04-04T10:30:00Z"
}
```

---

## 📱 Worker Interaction Examples

### Worker Joins (sends "JOIN" on WhatsApp)

**Bot Reply:**
```
Select your language:

1️⃣  English
2️⃣  हिंदी (Hindi)
3️⃣  ಕನ್ನಡ (Kannada)
4️⃣  தமிழ் (Tamil)
5️⃣  తెలుగు (Telugu)

Reply with number (1-5)
```

**Worker responds:** `2`

**Bot:** 
```
आप किस प्लेटफॉर्म पर काम करते हैं?

1️⃣ Zomato
2️⃣ Swiggy

1 या 2 से उत्तर दें
```

*... continues through platform, shift, plan selection ...*

**Final Bot Message:**
```
🎉 Registration complete!

Your coverage starts 24 hours from now.

💰 First week premium will be deducted from your wallet.

Questions? Type *HELP*
```

### Worker Checks Status (sends "STATUS")

**Bot Reply:**
```
✅ Current Status

Plan: Shield Plus
Platform: Zomato
Shift: Day

Coverage: Active ✅

For changes, type the respective command.
```

### Disruption Alert (Backend calls bot API)

```bash
POST /broadcast-disruption-alert
{
  "pincode": "560047",
  "dci_score": 78,
  "severity": "high",
  "worker_phones": ["919876543210", "918234567890"]
}
```

**Workers receive:**
```
🚨 Disruption detected in your zone (DCI: 78).
Your coverage is active. Payout will be calculated at end of shift.
```

### Payout Notification (Backend calls bot API)

```bash
POST /send-payout-confirmation
{
  "phone": "919876543210",
  "amount": 280,
  "reference_id": "RZP12345",
  "upi_id": "ravi@upi"
}
```

**Worker receives:**
```
💸 Payout Confirmed!
₹280 sent to ravi@upi
Ref: RZP12345

Your income is protected. 🛡️
```

---

## 📊 Session Storage

Sessions persist in `./data/sessions/`:

```bash
ls data/sessions/
# 919876543210.json
# 918074725459.json
# 917262819000.json
```

Each file is a snapshot of a user's state:

```json
{
  "userId": "550e8400-e29b-41d4-a716-446655440000",
  "phone": "919876543210",
  "language": "hi",
  "onboardingStep": "complete",
  "platform": "Zomato",
  "shift": "Day",
  "plan": "Shield Plus",
  "isOnboarded": true,
  "createdAt": "2026-04-04T09:00:00Z",
  "lastMessageAt": "2026-04-04T10:30:00Z",
  "status": "active"
}
```

**Recovery:** If something breaks, sessions are automatically restored on restart.

---

## 🛠 Development Mode

Auto-reload on file changes:

```bash
npm run dev
```

Uses `nodemon` to watch for changes. Perfect for testing message templates.

---

## 📦 Production Deployment

### AWS EC2 (Ubuntu 24.04 LTS)

```bash
# 1. SSH into your instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# 2. Install Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 3. Clone repository
git clone https://github.com/your-org/DEVTrails.git
cd DEVTrails/whatsapp-bot

# 4. Install dependencies
chmod +x install.sh && ./install.sh

# 5. Configure production .env
cat > .env << EOF
BOT_PORT=3001
BACKEND_URL=https://your-backend.com
DEBUG=false
EOF

# 6. Install PM2 (process manager)
npm install -g pm2

# 7. Start bot
pm2 start bot.js --name "gigkavach-bot"

# 8. Save process list
pm2 save
pm2 startup
```

### Render.com

1. Push code to GitHub
2. Create **Web Service** on Render
3. Connect your GitHub repo
4. Set environment variables:
   ```
   PUPPETEER_SKIP_DOWNLOAD=true
   BOT_PORT=10000
   BACKEND_URL=<your-backend-url>
   ```
5. Deploy!

### Docker

```dockerfile
FROM node:20-alpine

WORKDIR /app
COPY . .

ENV PUPPETEER_SKIP_DOWNLOAD=true
RUN npm install

EXPOSE 3001
CMD ["npm", "start"]
```

```bash
# Build
docker build -t gigkavach-bot .

# Run
docker run -it \
  -e PUPPETEER_SKIP_DOWNLOAD=true \
  -e BOT_PORT=3001 \
  -e BACKEND_URL=http://backend:8000 \
  -v $(pwd)/data:/app/data \
  -p 3001:3001 \
  gigkavach-bot
```

---

## 🐛 Troubleshooting

### "WhatsApp asks me to log in but QR doesn't work"

**Solution:**
```bash
# Clear the session
rm -rf data/sessions/*
npm start

# Scan new QR code
```

### "Port 3001 already in use"

**Solution:**
```bash
# Find what's using it
lsof -i :3001

# Kill it
kill -9 <PID>

# Or use different port
echo "BOT_PORT=3002" >> .env
npm start
```

### "Messages not reaching workers"

**Checklist:**
1. ✅ Is bot connected? `curl http://localhost:3001/health`
2. ✅ Is worker's WhatsApp account online?
3. ✅ Is phone number in correct format? (10 digits, no special chars)
4. ✅ Check logs: `npm start 2>&1 | tee bot.log`

### "Session lost after reboot"

This should NOT happen. But if it does:
```bash
# Check session files exist
ls -la data/sessions/

# If empty, rescan QR
rm -rf data/sessions/* && npm start
```

### "Deprecated npm warnings"

These are harmless and fixed in v2.0. They don't affect functionality.

---

## 🔒 Security Best Practices

- ✅ Store `.env` safely (never commit to Git)
- ✅ Use environment variables for secrets
- ✅ Keep `data/sessions/` backed up (contains WhatsApp session)
- ✅ In production, restrict bot API access (firewall/VPN)
- ✅ Rotate WhatsApp session monthly (delete and rescan QR)

---

## 📈 Scaling Notes

- Single bot instance can handle **1000+ concurrent workers**
- Each session file is ~1KB (1M workers = ~1GB storage)
- Message delivery is typically <2 seconds
- For massive scale (10M+), consider message queue (Redis/RabbitMQ)

---

## 🤔 FAQ

**Q: Can I run multiple bot instances?**  
A: Yes, but each needs a different phone number and session directory.

**Q: What if a worker loses their phone?**  
A: Bot session is tied to phone number. Old session persists. Worker can ping with new phone registered to backend.

**Q: Does bot work offline?**  
A: No, it needs active WhatsApp Web connection. If offline, messages queue in your WhatsApp and sync when online.

**Q: Can workers send multimedia (images, videos)?**  
A: Currently, bot only handles text. Images are ignored.

---

## 📚 API Reference

See [README.md](./README.md) for complete API documentation.

---

## 🎯 Next Steps

1. ✅ Install bot: `./install.sh`
2. ✅ Start bot: `npm start`
3. ✅ Scan QR code with WhatsApp
4. ✅ Test with curl or Postman
5. ✅ Integrate with backend API
6. ✅ Deploy to production

---

**Built by Team Quadcore for GigKavach** 🛡️  
**Questions?** Contact: varshit@gigkavach.com
