# 🤖 GigKavach WhatsApp Bot

WhatsApp integration for GigKavach using **whatsapp-web.js** with session persistence and full user context management.

## 📌 Overview

- **Technology**: Node.js + whatsapp-web.js + Express
- **Session Management**: File-based persistence (survives bot restarts)
- **User Context**: Language, onboarding state, worker profile
- **Multi-language**: 5 languages (English, Kannada, Hindi, Tamil, Telugu)
- **Integration**: REST API for backend communication (DCI alerts, payout confirmations)

## 📂 Structure

```
whatsapp-bot/
├── bot.js                      # Main bot with WhatsApp client and Express API
├── package.json               # Dependencies
├── .env.example               # Environment configuration
│
├── config/
│   └── messages.json          # Multilingual message templates (5 languages)
│
├── services/
│   ├── session-manager.js     # User session persistence
│   └── message-handler.js     # Message routing based on state
│
├── handlers/
│   ├── onboarding.js          # 7-step onboarding flow
│   └── commands.js            # Commands (STATUS, RENEW, SHIFT, APPEAL)
│
├── utils/
│   └── validators.js          # Input validation (UPI, pin code, phone)
│
└── data/
    ├── sessions/              # User session files (auto-created)
    └── users.json            # User registry (auto-created)
```

## 🚀 Getting Started

### 1. Install Dependencies

```bash
cd whatsapp-bot
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your backend URL
```

```env
BACKEND_URL=http://localhost:8000
BOT_PORT=3001
```

### 3. Run the Bot

```bash
npm start
```

**First run**: You'll see a QR code in the terminal. Scan it with WhatsApp to authenticate.

### Output:
```
📱 [GigKavach] Scan this QR code with your WhatsApp:
[QR CODE DISPLAYED]
✅ [GigKavach] WhatsApp bot is ready!
📲 Listening for incoming messages...
🔗 Bot API listening on port 3001
```

## 📱 User Workflow

### Onboarding (7 steps)

1. Worker sends: `JOIN`
2. **Language Selection**: Pick from 5 languages
3. **Platform**: Zomato or Swiggy
4. **Shift**: Morning/Day/Night/Flexible
5. **UPI ID**: For payouts (e.g., ravi@upi)
6. **Pin Codes**: Delivery zones (up to 5)
7. **Plan**: Shield Basic/Plus/Pro
8. **Complete**: Backend creates worker record → Coverage active from tomorrow

### Commands (After Onboarding)

- `STATUS` → Zone DCI score, coverage details
- `RENEW` → Renew policy for next week
- `SHIFT` → Update working hours
- `LANG` → Change language
- `APPEAL` → Contest fraud decision
- `HELP` → Show all commands

### Disruption Alerts

When DCI ≥ 65 in worker's zone:
```
🚨 Disruption detected in your zone (DCI: 78).
Your coverage is active. Payout will be calculated at end of your shift today.
```

### Payout Confirmation

After payout processed:
```
💸 ₹280 sent to ravi@upi. Ref: RZP12345.
Your income is protected. 🛡️
```

## 🔗 API Endpoints

### Inbound (Web UI triggers bot to send messages)

**POST /send-message**  
Send a message to a worker
```bash
curl -X POST http://localhost:3001/send-message \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "918074725459",
    "message": "Test message",
    "messageType": "disruption_alert"
  }'
```

**POST /broadcast-dci-alert**  
Broadcast DCI alert to multiple workers in a zone
```bash
curl -X POST http://localhost:3001/broadcast-dci-alert \
  -H "Content-Type: application/json" \
  -d '{
    "pincode": "560047",
    "dci_score": 78,
    "worker_phones": ["918074725459", "919876543210"],
    "severity": "high"
  }'
```

**POST /send-payout-confirmation**  
Send payout confirmation to a worker
```bash
curl -X POST http://localhost:3001/send-payout-confirmation \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "918074725459",
    "amount": 280,
    "upi": "ravi@upi",
    "ref": "RZP12345",
    "language": "en"
  }'
```

**GET /health**  
Health check
```bash
curl http://localhost:3001/health
```

**GET /sessions**  
Get active session count
```bash
curl http://localhost:3001/sessions
```

## 🔌 Backend Integration

The backend calls the bot via REST API (see above endpoints).

**Backend endpoints to call bot:**

```python
# Example: When DCI ≥ 65 in a zone
POST http://localhost:3001/broadcast-dci-alert

# Example: When payout is sent
POST http://localhost:3001/send-payout-confirmation

# Or use backend API which forwards to bot:
POST /api/v1/whatsapp/broadcast-dci-alert
POST /api/v1/whatsapp/send-payout-confirmation
```

## 💾 Session Persistence

User sessions are stored in `./data/sessions/{phone}.json`:

```json
{
  "userId": "550e8400-e29b-41d4-a716-446655440000",
  "phone": "918074725459",
  "language": "en",
  "onboardingStep": "complete",
  "tempData": {
    "platform": "Zomato",
    "shift": "Day (9AM–9PM)",
    "upi": "ravi@upi",
    "pincodes": ["560047", "560034"],
    "plan": "Shield Plus"
  },
  "isOnboarded": true,
  "createdAt": "2026-04-03T10:30:00Z",
  "lastMessageAt": "2026-04-03T11:45:00Z",
  "status": "active",
  "workerData": {
    "worker_id": "W123",
    "policy_id": "P456",
    "plan": "Plus",
    ...
  }
}
```

Sessions survive bot restarts—no re-authentication needed.

## 🌍 Multilingual Support

All 30+ messages translated in `config/messages.json`:

- **English** (en)
- **Kannada** (kn)
- **Hindi** (hi)
- **Tamil** (ta)
- **Telugu** (te)

Messages auto-selected based on worker's language preference.

## 🐛 Troubleshooting

### QR Code Not Appearing
- Bot might be running without TTY. Run: `node bot.js` in a proper terminal
- Check that the whatsapp-web.js session doesn't already exist in `./data/.wwebjs_auth`

### Messages Not Sending
- Check that backend is running on `BACKEND_URL`
- Verify WhatsApp account is logged in (no "Temporarily unavailable" message)
- Check logs for errors

### Session Lost After Restart
- Sessions are stored in `./data/sessions/`
- WhatsApp authentication cached in `./data/.wwebjs_auth/` (auto-managed by whatsapp-web.js)
- Should persist across restarts

### Backend Can't Reach Bot
- Ensure bot is listening on correct port (default 3001)
- In production, make sure firewall allows traffic to bot port
- Use `curl http://localhost:3001/health` to test connectivity

## 📦 Production Deployment

### AWS EC2

```bash
# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Clone repo, install dependencies
git clone <repo>
cd whatsapp-bot
npm install

# Use PM2 for process management
npm install -g pm2
pm2 start bot.js --name "gigkavach-bot"
pm2 save
pm2 startup

# Configure .env with production URLs
```

### Environment Variables

```env
# Production
BACKEND_URL=https://gigkavach-backend.onrender.com
BOT_PORT=3001
LOG_LEVEL=info
```

### Security

- Bot service should be behind firewall (only backend calls it)
- Don't expose port 3001 publicly; use VPC or IP whitelisting
- Rotate WhatsApp session regularly
- Add authentication to bot endpoints if exposed

## 📊 Monitoring

Check bot health via backend:

```bash
curl http://your-backend.com/api/v1/whatsapp/bot-health
```

Monitor active sessions:

```bash
curl http://localhost:3001/sessions
```

## 🤔 FAQ

**Q: Does the bot support group messages?**  
A: No, group messages are explicitly ignored.

**Q: What if WhatsApp blocks the session?**  
A: Delete `./data/.wwebjs_auth/` and re-scan the QR code.

**Q: Can multiple workers use the same phone?**  
A: No, one phone = one worker account. Session is phone-based.

**Q: Does the bot work on WhatsApp Business?**  
A: Currently uses regular WhatsApp. Business integration requires additional setup.

---

**Built by Team Quadcore for GigKavach** 🛡️  
**Last Updated: April 3, 2026**
