#!/usr/bin/env node

/**
 * GigKavach WhatsApp Bot v2.0
 * ═════════════════════════════════════════════════════════════════
 * WhatsApp bot for worker onboarding and disruption alerts
 * Using whatsapp-web.js with LocalAuth for session persistence
 * ═════════════════════════════════════════════════════════════════
 */

import pkg from 'whatsapp-web.js';
const { Client, LocalAuth } = pkg;
import qrcode from 'qrcode-terminal';
import express from 'express';
import bodyParser from 'body-parser';
import dotenv from 'dotenv';
import chalk from 'chalk';
import { fileURLToPath } from 'url';
import { dirname } from 'path';
import { execSync } from 'child_process';
import { messageQueue } from './services/message-queue.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

dotenv.config();

// ═════════════════════════════════════════════════════════════════
// Configuration
// ═════════════════════════════════════════════════════════════════

const PORT = process.env.BOT_PORT || 3001;
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const DEBUG = process.env.DEBUG === 'true';

const log = {
  info: (msg) => console.log(chalk.blue('ℹ️'), msg),
  success: (msg) => console.log(chalk.green('✅'), msg),
  warn: (msg) => console.log(chalk.yellow('⚠️'), msg),
  error: (msg) => console.log(chalk.red('❌'), msg),
  debug: (msg) => DEBUG && console.log(chalk.gray('🔍'), msg),
  message: (msg) => console.log(chalk.cyan('💬'), msg),
};

// ═════════════════════════════════════════════════════════════════
// Helper: Find Chrome/Chromium Executable
// ═════════════════════════════════════════════════════════════════

function findChromePath() {
  const possiblePaths = [
    // macOS
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    
    // Linux
    '/usr/bin/google-chrome',
    '/usr/bin/chromium-browser',
    '/usr/bin/chromium',
    '/snap/bin/chromium',
    
    // Windows (WSL)
    '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe',
    '/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  ];
  
  for (const path of possiblePaths) {
    try {
      execSync(`test -f "${path}"`, { stdio: 'pipe' });
      log.info(`Found Chrome at: ${path}`);
      return path;
    } catch (e) {
      // Continue to next path
    }
  }
  
  return undefined;
}

// ═════════════════════════════════════════════════════════════════
// WhatsApp Client Initialization
// ═════════════════════════════════════════════════════════════════

log.info('🤖 Initializing GigKavach WhatsApp Bot...');

const chromePath = findChromePath();
if (!chromePath) {
  log.warn('⚠️ Chrome/Chromium not found in standard locations');
  log.warn('Install Chrome/Chromium or set PUPPETEER_EXECUTABLE_PATH env variable');
}

const client = new Client({
  authStrategy: new LocalAuth({
    clientId: 'gigkavach-bot',
  }),
  puppeteer: {
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--disable-dev-tools',
      '--no-first-run',
      '--no-default-browser-check',
    ],
    headless: 'new',
    timeout: 0,
    executablePath: chromePath || process.env.PUPPETEER_EXECUTABLE_PATH,
  },
  authTimeoutMs: 60000,
  qrMaxRetries: 10,
  takeoverOnConflict: true,
  takeoverTimeoutMs: 0,
});


// ═════════════════════════════════════════════════════════════════
// WhatsApp Client Events
// ═════════════════════════════════════════════════════════════════

/**
 * QR Code Generation - shown only on first login
 */
client.on('qr', (qr) => {
  log.warn('📱 SCAN THIS QR CODE WITH YOUR WHATSAPP TO LOGIN');
  log.warn('(Session will be saved for future auto-login)\n');
  qrcode.generate(qr, { small: true });
});

/**
 * Authentication Failure
 */
client.on('auth_failure', (msg) => {
  log.error(`Authentication failed: ${msg}`);
});

/**
 * Disconnection Handler
 */
client.on('disconnected', (reason) => {
  log.warn(`Bot disconnected: ${reason}`);
  log.info('Attempting to reconnect...');
});

// ═════════════════════════════════════════════════════════════════
// Message Queue Processor
// ═════════════════════════════════════════════════════════════════
/**
 * Process queued messages with exponential backoff retry
 * Runs every 5 seconds to check for pending messages
 */
async function processMessageQueue() {
  try {
    const item = messageQueue.getNext();
    if (!item) return; // No pending messages

    try {
      const phoneFormatted = `${item.phoneNumber}@c.us`;
      await client.sendMessage(phoneFormatted, item.messageBody);
      messageQueue.markSent(item.id);
      log.success(`[QUEUE SENT] ${item.phoneNumber}: ${item.metadata.type || 'message'}`);
    } catch (error) {
      messageQueue.markForRetry(item.id, error);
      log.warn(`[QUEUE RETRY] ${item.phoneNumber}: ${error.message}`);
    }
  } catch (error) {
    log.error(`Queue processor error: ${error.message}`);
  }
}

// Start queue processor after bot initializes
let queueProcessorInterval;
client.on('ready', () => {
  log.success('WhatsApp bot is ready and listening for messages!');
  log.info(`Backend URL: ${BACKEND_URL}`);
  log.info(`Bot API listening on port ${PORT}`);
  
  // Start processing queued messages
  queueProcessorInterval = setInterval(processMessageQueue, 5000);
  log.info('Message queue processor started (5s intervals)');
});

/**
 * Message Handler - Main inbound message processor
 * FORWARDS TO BACKEND WEBHOOK (Centralized Logic)
 */
client.on('message', async (msg) => {
  try {
    // Ignore messages sent by the bot itself to avoid reply loops.
    if (msg.fromMe) return;

    // Ignore group messages and status broadcasts
    if (msg.from.endsWith('@g.us') || msg.from === 'status@broadcast') return;

    const phone = msg.from.replace('@c.us', '');
    const messageBody = msg.body.trim();

    log.message(`Received from ${phone}: "${messageBody.substring(0, 40)}..."`);

    // ── Forward to Backend Webhook ──────────────────────────────────────────
    // The Python backend handles state, Redis, and business logic.
    // It will call our /send-message API to reply.
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/whatsapp/webhook`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phone: phone,
          body: messageBody,
          timestamp: new Date().toISOString()
        }),
      });

      if (!response.ok) {
        log.error(`Backend webhook failed: ${response.status}`);
      } else {
        const data = await response.json().catch(() => ({}));
        const replyText = typeof data?.reply === 'string' ? data.reply.trim() : '';

        if (replyText) {
          await msg.reply(replyText);
          log.debug(`Replied directly to ${phone}`);
        } else if (data?.detail || data?.message || data?.status === 'error') {
          const fallbackText = data.detail || data.message || `Backend webhook failed (${response.status})`;
          await msg.reply(`⚠️ ${fallbackText}`);
        } else {
          log.warn(`Backend responded without a reply for ${phone}`);
          await msg.reply('✅ Message received. We are processing it now.');
        }
      }
    } catch (backendError) {
      log.error(`Failed to reach backend: ${backendError.message}`);
      await msg.reply('⚠️ GigKavach backend is temporarily offline. Please try again in a moment.');
    }

  } catch (error) {
    log.error(`Message processing error: ${error.message}`);
  }
});

// ═════════════════════════════════════════════════════════════════
// Express API Server for Backend Integration
// ═════════════════════════════════════════════════════════════════

const app = express();
app.use(bodyParser.json({ limit: '10mb' }));
app.use(bodyParser.urlencoded({ limit: '10mb', extended: true }));

/**
 * POST /send-message
 * Backend → Bot: Send a message to a specific worker
 * 
 * Uses message queue with exponential backoff retry for reliability.
 * If message fails to send, it will be retried automatically.
 *
 * Body: { phone: "919876543210", message: "Your content", messageType: "alert|confirmation|etc" }
 */
app.post('/send-message', async (req, res) => {
  try {
    const { phone, message, messageType } = req.body;

    if (!phone || !message) {
      return res.status(400).json({
        status: 'error',
        message: 'phone and message are required',
      });
    }

    // Enqueue message for sending (with automatic retry)
    const queueItem = await messageQueue.enqueue(phone, message, {
      type: messageType || 'message',
      backend_request: new Date().toISOString(),
    });

    log.info(`[QUEUE] Message enqueued for ${phone} (ID: ${queueItem.id})`);

    return res.json({
      status: 'success',
      phone,
      messageType,
      queue_id: queueItem.id,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    log.error(`Send message failed: ${error.message}`);
    return res.status(500).json({
      status: 'error',
      message: error.message,
    });
  }
});

/**
 * POST /broadcast-disruption-alert
 * Backend → Bot: Broadcast disruption alert to all workers in a zone
 *
 * Body: {
 *   pincode: "560047",
 *   dci_score: 75,
 *   severity: "high|moderate|severe",
 *   worker_phones: ["919876543210", ...],
 *   message_template: "alert_text" (optional)
 * }
 */
app.post('/broadcast-disruption-alert', async (req, res) => {
  try {
    const { pincode, dci_score, severity, worker_phones, message_template } = req.body;

    if (!pincode || dci_score === undefined || !Array.isArray(worker_phones)) {
      return res.status(400).json({
        status: 'error',
        message: 'pincode, dci_score, and worker_phones array are required',
      });
    }

    log.warn(`🚨 BROADCASTING DISRUPTION ALERT - Pincode: ${pincode}, DCI: ${dci_score}`);

    const baseMessage =
      message_template ||
      `🚨 Disruption detected in your zone (DCI: ${dci_score}).\nYour coverage is active. Payout will be calculated at end of shift.`;

    const results = {
      sent: [],
      failed: [],
    };

    for (const phone of worker_phones) {
      try {
        await messageQueue.enqueue(phone, baseMessage, {
          type: 'disruption_broadcast',
          pincode: pincode,
          dci: dci_score,
          severity: severity
        });
        results.sent.push(phone);
      } catch (error) {
        log.error(`Failed to enqueue for ${phone}: ${error.message}`);
        results.failed.push({ phone, error: error.message });
      }
    }

    log.success(`Broadcast complete: ${results.sent.length} sent, ${results.failed.length} failed`);

    return res.json({
      status: 'success',
      pincode,
      dci_score,
      severity,
      sent_count: results.sent.length,
      failed_count: results.failed.length,
      failed_details: results.failed,
    });
  } catch (error) {
    log.error(`Broadcast error: ${error.message}`);
    return res.status(500).json({
      status: 'error',
      message: error.message,
    });
  }
});

/**
 * POST /send-payout-confirmation
 * Backend → Bot: Send payout confirmation to worker
 *
 * Body: {
 *   phone: "919876543210",
 *   amount: 280,
 *   reference_id: "RZP12345",
 *   upi_id: "worker@upi"
 * }
 */
app.post('/send-payout-confirmation', async (req, res) => {
  try {
    const { phone, amount, reference_id, upi_id } = req.body;

    if (!phone || !amount || !reference_id) {
      return res.status(400).json({
        status: 'error',
        message: 'phone, amount, and reference_id are required',
      });
    }

    const message = `💸 Payout Confirmed!\n₹${amount} sent to ${upi_id || 'your UPI'}\nRef: ${reference_id}\n\nYour income is protected. 🛡️`;

    const phoneFormatted = `${phone}@c.us`;
    await client.sendMessage(phoneFormatted, message);

    log.info(`[PAYOUT] ₹${amount} to ${phone} (Ref: ${reference_id})`);

    return res.json({
      status: 'success',
      phone,
      amount,
      reference_id,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    log.error(`Payout confirmation failed: ${error.message}`);
    return res.status(500).json({
      status: 'error',
      message: error.message,
    });
  }
});

/**
 * POST /send-fraud-alert
 * Backend → Bot: Send fraud alert/flag to worker
 *
 * Body: {
 *   phone: "919876543210",
 *   tier: "soft|hard|blacklist",
 *   reason: "GPS_MISMATCH|CLAIM_BURST|..."
 * }
 */
app.post('/send-fraud-alert', async (req, res) => {
  try {
    const { phone, tier, reason } = req.body;

    if (!phone || !tier) {
      return res.status(400).json({
        status: 'error',
        message: 'phone and tier are required',
      });
    }

    let message = '';
    if (tier === 'soft') {
      message =
        '⚠️ Your recent claim is under verification due to signal anomalies in your zone.\nNo action needed. We will auto-confirm within 48 hours.';
    } else if (tier === 'hard') {
      message =
        '🚫 This claim has been flagged for manual review.\nYour payout is withheld. Use APPEAL command to contest (48 hours).';
    } else if (tier === 'blacklist') {
      message = '❌ Your account has been suspended due to fraudulent activity. Contact support.';
    }

    if (message) {
      const phoneFormatted = `${phone}@c.us`;
      await client.sendMessage(phoneFormatted, message);
      log.warn(`[FRAUD ALERT] Tier: ${tier}, Reason: ${reason}, Phone: ${phone}`);
    }

    return res.json({
      status: 'success',
      phone,
      tier,
      reason,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    log.error(`Fraud alert failed: ${error.message}`);
    return res.status(500).json({
      status: 'error',
      message: error.message,
    });
  }
});

/**
 * GET /health
 * Liveness check for the bot
 */
app.get('/health', (req, res) => {
  return res.json({
    status: 'ok',
    bot_name: 'GigKavach WhatsApp Bot v2.0',
    connected: client.pupPage ? true : false,
    timestamp: new Date().toISOString(),
    uptime_seconds: process.uptime(),
  });
});

/**
 * GET /stats
 * Bot statistics and session info
 */
app.get('/stats', (req, res) => {
  const queueStats = messageQueue.getStats();
  
  return res.json({
    status: 'ok',
    queue: queueStats,
    uptime_seconds: process.uptime(),
    timestamp: new Date().toISOString(),
  });
});

/**
 * GET /queue/status
 * Message queue status and stats
 */
app.get('/queue/status', (req, res) => {
  const stats = messageQueue.getStats();
  return res.json({
    status: 'ok',
    queue: stats,
    timestamp: new Date().toISOString(),
  });
});

/**
 * GET /queue/dead-letters
 * Get permanently failed messages (dead letter queue)
 */
app.get('/queue/dead-letters', (req, res) => {
  const limit = Math.min(parseInt(req.query.limit) || 20, 100);
  const deadLetters = messageQueue.getDeadLetters(limit);
  return res.json({
    status: 'ok',
    count: deadLetters.length,
    messages: deadLetters,
    timestamp: new Date().toISOString(),
  });
});

/**
 * DELETE /queue/dead-letter/:messageId
 * Remove a message from dead letter queue (allow manual recovery if message was false positive)
 */
app.delete('/queue/dead-letter/:messageId', (req, res) => {
  const { messageId } = req.params;
  try {
    messageQueue.clearDeadLetter(messageId);
    return res.json({
      status: 'ok',
      message: `Dead letter ${messageId} cleared`,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    return res.status(500).json({
      status: 'error',
      message: error.message,
    });
  }
});

// ═════════════════════════════════════════════════════════════════
// Start Server
// ═════════════════════════════════════════════════════════════════

app.listen(PORT, () => {
  log.success(`GigKavach Bot API Server Started`);
  log.info(`🌐 Listening on http://localhost:${PORT}`);
  log.info('Available endpoints:');
  log.info('  POST   /send-message');
  log.info('  POST   /broadcast-disruption-alert');
  log.info('  POST   /send-payout-confirmation');
  log.info('  POST   /send-fraud-alert');
  log.info('  GET    /health');
  log.info('  GET    /stats');
  log.info('\nStarting WhatsApp client...\n');
});

// Initialize WhatsApp client
client.initialize();

// ═════════════════════════════════════════════════════════════════
// Graceful Shutdown
// ═════════════════════════════════════════════════════════════════

process.on('SIGINT', async () => {
  log.warn('\n\nShutting down gracefully...');
  
  // Stop queue processor
  if (queueProcessorInterval) {
    clearInterval(queueProcessorInterval);
    log.info('Message queue processor stopped');
  }
  
  try {
    await client.destroy();
    log.success('WhatsApp client destroyed');
  } catch (error) {
    log.error(`Error during shutdown: ${error.message}`);
  }
  process.exit(0);
});

process.on('SIGTERM', async () => {
  log.warn('\n\nTermination signal received. Shutting down...');
  
  // Stop queue processor
  if (queueProcessorInterval) {
    clearInterval(queueProcessorInterval);
    log.info('Message queue processor stopped');
  }
  
  try {
    await client.destroy();
    log.success('WhatsApp client destroyed');
  } catch (error) {
    log.error(`Error during shutdown: ${error.message}`);
  }
  process.exit(0);
});

// Error handlers
process.on('uncaughtException', (error) => {
  log.error(`Uncaught Exception: ${error.message}`);
  console.error(error);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  log.error(`Unhandled Rejection at ${promise}: ${reason}`);
});

export { client };

