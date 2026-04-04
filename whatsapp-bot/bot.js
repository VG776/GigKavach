/**
 * bot.js
 * ─────────────────────────────────────────
 * Main WhatsApp bot using whatsapp-web.js
 * Handles:
 * - Inbound messages from workers
 * - Session persistence
 * - Outbound alerts and confirmations from backend
 */

import { Client, LocalAuth } from 'whatsapp-web.js';
import qrcode from 'qrcode-terminal';
import axios from 'axios';
import express from 'express';
import bodyParser from 'body-parser';
import dotenv from 'dotenv';
import { routeMessage } from './services/message-handler.js';

dotenv.config();

// ─────────────────────────────────────────────────────────────────
// WhatsApp Client Configuration
// ─────────────────────────────────────────────────────────────────

const client = new Client({
  authStrategy: new LocalAuth(),
  puppeteer: {
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
    headless: true,
  },
});

// ─────────────────────────────────────────────────────────────────
// QR Code Display (for initial login)
// ─────────────────────────────────────────────────────────────────

client.on('qr', (qr) => {
  console.log('\n📱 [GigKavach] Scan this QR code with your WhatsApp:');
  qrcode.generate(qr, { small: true });
});

// ─────────────────────────────────────────────────────────────────
// Ready Event
// ─────────────────────────────────────────────────────────────────

client.on('ready', () => {
  console.log('✅ [GigKavach] WhatsApp bot is ready!');
  console.log('📲 Listening for incoming messages...');
  console.log('🔗 Bot API listening on port 3001');
});

// ─────────────────────────────────────────────────────────────────
// Inbound Message Handler
// ─────────────────────────────────────────────────────────────────

client.on('message', async (msg) => {
  // Ignore group messages
  if (msg.from.endsWith('@g.us')) return;

  const phone = msg.from; // e.g., "918074725459@c.us"
  const phoneClean = phone.replace('@c.us', ''); // "918074725459"
  const body = msg.body.trim();

  console.log(`\n📨 [INBOUND] from=${phoneClean} body=${body.substring(0, 50)}...`);

  try {
    // Route message to appropriate handler
    const replyText = await routeMessage(phoneClean, body);

    if (replyText) {
      // Send reply
      await msg.reply(replyText);
      console.log(`💬 [REPLY] to=${phoneClean} msg=${replyText.substring(0, 60)}...`);
    }
  } catch (error) {
    console.error(`❌ [ERROR] Processing message from ${phoneClean}:`, error.message);

    const errorReply =
      '⚠️ Oops! Something went wrong. Please try again or contact support.';
    await msg.reply(errorReply);
  }
});

// ─────────────────────────────────────────────────────────────────
// Express API Server (for backend → bot communication)
// ─────────────────────────────────────────────────────────────────

const app = express();
app.use(bodyParser.json());

/**
 * POST /send-message
 * Called by backend to send outbound messages (alerts, confirmations)
 *
 * Body: {
 *   "phone": "918074725459",
 *   "message": "🚨 Disruption detected...",
 *   "messageType": "disruption_alert|payout_sent|fraud_flag|etc"
 * }
 */
app.post('/send-message', async (req, res) => {
  const { phone, message, messageType } = req.body;

  if (!phone || !message) {
    return res.status(400).json({
      status: 'error',
      message: 'phone and message are required',
    });
  }

  try {
    const phoneFormatted = `${phone}@c.us`;
    await client.sendMessage(phoneFormatted, message);

    console.log(`📤 [OUTBOUND] to=${phone} type=${messageType} msg=${message.substring(0, 60)}...`);

    res.json({
      status: 'ok',
      message: 'Message sent successfully',
      phone,
      messageType,
    });
  } catch (error) {
    console.error(`❌ [SEND ERROR] to=${phone}:`, error.message);

    res.status(500).json({
      status: 'error',
      message: error.message,
      phone,
    });
  }
});

/**
 * POST /broadcast-dci-alert
 * Called when DCI ≥ 65 in a zone
 * Sends disruption alerts to all active workers in that zone
 *
 * Body: {
 *   "pincode": "560047",
 *   "dci_score": 78,
 *   "worker_phones": ["918074725459", "919876543210", ...],
 *   "severity": "high",
 *   "language": "en" (optional)
 * }
 */
app.post('/broadcast-dci-alert', async (req, res) => {
  const { pincode, dci_score, worker_phones, severity } = req.body;

  if (!pincode || !dci_score || !worker_phones || !Array.isArray(worker_phones)) {
    return res.status(400).json({
      status: 'error',
      message: 'pincode, dci_score, and worker_phones array are required',
    });
  }

  console.log(`\n🚨 [BROADCAST] DCI Alert for pincode ${pincode}`);
  console.log(`   DCI: ${dci_score} | Severity: ${severity}`);
  console.log(`   Sending to ${worker_phones.length} workers...`);

  const sent = [];
  const failed = [];

  for (const phone of worker_phones) {
    try {
      const message = `🚨 Disruption detected in your zone (DCI: ${dci_score}).\nYour coverage is active. Payout will be calculated at end of your shift today.`;

      const phoneFormatted = `${phone}@c.us`;
      await client.sendMessage(phoneFormatted, message);

      sent.push(phone);
      console.log(`   ✅ Sent to ${phone}`);
    } catch (error) {
      failed.push({ phone, error: error.message });
      console.log(`   ❌ Failed to send to ${phone}: ${error.message}`);
    }
  }

  res.json({
    status: 'ok',
    message: 'Broadcast completed',
    pincode,
    dci_score,
    sent: sent.length,
    failed: failed.length,
    failedDetails: failed,
  });
});

/**
 * POST /send-payout-confirmation
 * Called when payout is sent to a worker
 *
 * Body: {
 *   "phone": "918074725459",
 *   "amount": 280,
 *   "upi": "ravi@upi",
 *   "ref": "RZP12345",
 *   "language": "en"
 * }
 */
app.post('/send-payout-confirmation', async (req, res) => {
  const { phone, amount, upi, ref, language = 'en' } = req.body;

  if (!phone || !amount || !upi || !ref) {
    return res.status(400).json({
      status: 'error',
      message: 'phone, amount, upi, and ref are required',
    });
  }

  try {
    const message = `💸 ₹${amount} sent to ${upi}. Ref: ${ref}.\nYour income is protected. 🛡️`;

    const phoneFormatted = `${phone}@c.us`;
    await client.sendMessage(phoneFormatted, message);

    console.log(`💰 [PAYOUT] to=${phone} amount=₹${amount} ref=${ref}`);

    res.json({
      status: 'ok',
      message: 'Payout confirmation sent',
      phone,
      amount,
      ref,
    });
  } catch (error) {
    console.error(`❌ [PAYOUT ERROR] to=${phone}:`, error.message);

    res.status(500).json({
      status: 'error',
      message: error.message,
      phone,
    });
  }
});

/**
 * GET /health
 * Health check endpoint
 */
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    bot_connected: client.pupPage ? true : false,
    timestamp: new Date().toISOString(),
  });
});

/**
 * GET /sessions
 * Get count of active sessions (for monitoring)
 */
app.get('/sessions', (req, res) => {
  const SessionManager = (
    await import('./services/session-manager.js')
  ).default;
  const sessions = SessionManager.getAllSessions();

  res.json({
    status: 'ok',
    total_sessions: Object.keys(sessions).length,
    active_sessions: Object.values(sessions).filter((s) => s.status === 'active').length,
  });
});

// ─────────────────────────────────────────────────────────────────
// Start Server
// ─────────────────────────────────────────────────────────────────

const PORT = process.env.BOT_PORT || 3001;

app.listen(PORT, () => {
  console.log(`\n🤖 [GigKavach Bot API] listening on port ${PORT}`);
  console.log(`   POST http://localhost:${PORT}/send-message`);
  console.log(`   POST http://localhost:${PORT}/broadcast-dci-alert`);
  console.log(`   POST http://localhost:${PORT}/send-payout-confirmation`);
  console.log(`   GET  http://localhost:${PORT}/health\n`);
});

// Initialize WhatsApp client
client.initialize();

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n\n✋ [GigKavach] Shutting down gracefully...');
  client.destroy();
  process.exit(0);
});
