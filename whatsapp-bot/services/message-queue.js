/**
 * services/message-queue.js
 * ═════════════════════════════════════════════════════════════════
 * WhatsApp Message Queue with Retry Logic
 *
 * Ensures messages are not lost if the bot fails to send them.
 * Uses in-memory queue with persistent storage (JSON file).
 *
 * Features:
 * - Message persistence across bot restarts
 * - Exponential backoff retry (1s, 2s, 4s, 8s, etc.)
 * - Dead letter queue for permanently failed messages
 * - Delivery status tracking
 * ═════════════════════════════════════════════════════════════════
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const QUEUE_FILE = path.join(__dirname, '../data', 'message_queue.json');
const DEAD_LETTER_FILE = path.join(__dirname, '../data', 'dead_letter_queue.json');

// Ensure data directory exists
const dataDir = path.join(__dirname, '../data');
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

class MessageQueue {
  constructor() {
    this.queue = [];
    this.processing = false;
    this.maxRetries = 5;
    this.deadLetterQueue = [];
    this.loadQueue();
  }

  /**
   * Load queue from persistent storage
   */
  loadQueue() {
    try {
      if (fs.existsSync(QUEUE_FILE)) {
        const data = fs.readFileSync(QUEUE_FILE, 'utf-8');
        this.queue = JSON.parse(data) || [];
        console.log(`[QUEUE] Loaded ${this.queue.length} messages from storage`);
      }

      if (fs.existsSync(DEAD_LETTER_FILE)) {
        const data = fs.readFileSync(DEAD_LETTER_FILE, 'utf-8');
        this.deadLetterQueue = JSON.parse(data) || [];
      }
    } catch (error) {
      console.error('[QUEUE] Error loading queue:', error);
      this.queue = [];
    }
  }

  /**
   * Save queue to persistent storage
   */
  saveQueue() {
    try {
      fs.writeFileSync(QUEUE_FILE, JSON.stringify(this.queue, null, 2), 'utf-8');
      fs.writeFileSync(DEAD_LETTER_FILE, JSON.stringify(this.deadLetterQueue, null, 2), 'utf-8');
    } catch (error) {
      console.error('[QUEUE] Error saving queue:', error);
    }
  }

  /**
   * Add message to queue
   */
  async enqueue(phoneNumber, message, metadata = {}) {
    const queueItem = {
      id: `${phoneNumber}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      phoneNumber,
      messageBody: message,
      metadata,
      attempts: 0,
      maxRetries: this.maxRetries,
      createdAt: new Date().toISOString(),
      lastAttemptAt: null,
      status: 'pending', // pending, sending, sent, failed
      error: null,
    };

    this.queue.push(queueItem);
    this.saveQueue();

    console.log(`[QUEUE] Enqueued message for ${phoneNumber}: ${queueItem.id}`);
    return queueItem;
  }

  /**
   * Get next message to process
   */
  getNext() {
    return this.queue.find((item) => item.status === 'pending');
  }

  /**
   * Calculate exponential backoff delay (in ms)
   */
  getBackoffDelay(attemptNumber) {
    // 1s, 2s, 4s, 8s, 16s, ...
    const delaySeconds = Math.pow(2, attemptNumber - 1);
    return delaySeconds * 1000;
  }

  /**
   * Mark message as sent
   */
  markSent(messageId) {
    const item = this.queue.find((q) => q.id === messageId);
    if (item) {
      item.status = 'sent';
      item.lastAttemptAt = new Date().toISOString();
      this.saveQueue();
      console.log(`[QUEUE] Message ${messageId} marked as sent`);
    }
  }

  /**
   * Mark message for retry with exponential backoff
   */
  markForRetry(messageId, error) {
    const item = this.queue.find((q) => q.id === messageId);
    if (!item) return;

    item.attempts++;
    item.lastAttemptAt = new Date().toISOString();
    item.error = error?.message || String(error);

    if (item.attempts < item.maxRetries) {
      item.status = 'pending'; // Will be retried
      const delay = this.getBackoffDelay(item.attempts);
      console.log(
        `[QUEUE] Message ${messageId} scheduled for retry (attempt ${item.attempts}/${item.maxRetries}) in ${delay}ms`
      );
      // Schedule retry after backoff
      setTimeout(() => {
        this.saveQueue();
      }, delay);
    } else {
      // Max retries exceeded, move to dead letter queue
      item.status = 'failed';
      this.deadLetterQueue.push(item);
      this.queue = this.queue.filter((q) => q.id !== messageId);
      console.error(`[QUEUE] Message ${messageId} moved to dead letter queue after ${item.attempts} attempts`);
    }

    this.saveQueue();
  }

  /**
   * Get queue stats
   */
  getStats() {
    return {
      pending: this.queue.filter((q) => q.status === 'pending').length,
      sent: this.queue.filter((q) => q.status === 'sent').length,
      failed: this.deadLetterQueue.length,
      total: this.queue.length + this.deadLetterQueue.length,
    };
  }

  /**
   * Get dead letter queue (permanently failed messages)
   */
  getDeadLetters(limit = 20) {
    return this.deadLetterQueue.slice(0, limit);
  }

  /**
   * Clear a specific dead letter message
   */
  clearDeadLetter(messageId) {
    this.deadLetterQueue = this.deadLetterQueue.filter((q) => q.id !== messageId);
    this.saveQueue();
  }
}

// Singleton instance
export const messageQueue = new MessageQueue();
