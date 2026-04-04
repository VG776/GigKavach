/**
 * services/session-manager.js
 * ─────────────────────────────────────────
 * Manages user sessions with persistent storage.
 * Tracks onboarding state, language, and user preferences.
 */

import fs from 'fs';
import path from 'path';
import { v4 as uuidv4 } from 'uuid';

const SESSIONS_DIR = './data/sessions';
const USERS_DB = './data/users.json';

// Ensure directories exist
const ensureDir = (dir) => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
};

ensureDir(SESSIONS_DIR);

/**
 * Session structure:
 * {
 *   userId: UUID,
 *   phone: WhatsApp number,
 *   language: 'en' | 'kn' | 'hi' | 'ta' | 'te',
 *   onboardingStep: 'start' | 'language' | 'platform' | 'shift' | 'upi' | 'pincode' | 'plan' | 'complete',
 *   tempData: { platform, shift, upi, pincodes, plan },
 *   isOnboarded: boolean,
 *   createdAt: timestamp,
 *   lastMessageAt: timestamp,
 *   status: 'active' | 'inactive'
 * }
 */

const SessionManager = {
  /**
   * Get or create a session for a phone number
   */
  getOrCreateSession(phone) {
    const sessionFile = path.join(SESSIONS_DIR, `${phone}.json`);

    if (fs.existsSync(sessionFile)) {
      const data = fs.readFileSync(sessionFile, 'utf-8');
      return JSON.parse(data);
    }

    // Create new session
    const session = {
      userId: uuidv4(),
      phone,
      language: 'en', // Default to English
      onboardingStep: 'start',
      tempData: {},
      isOnboarded: false,
      createdAt: new Date().toISOString(),
      lastMessageAt: new Date().toISOString(),
      status: 'active',
    };

    this.saveSession(phone, session);
    return session;
  },

  /**
   * Save session to file
   */
  saveSession(phone, session) {
    const sessionFile = path.join(SESSIONS_DIR, `${phone}.json`);
    fs.writeFileSync(sessionFile, JSON.stringify(session, null, 2));
  },

  /**
   * Update session state
   */
  updateSession(phone, updates) {
    const session = this.getOrCreateSession(phone);
    const updated = {
      ...session,
      ...updates,
      lastMessageAt: new Date().toISOString(),
    };
    this.saveSession(phone, updated);
    return updated;
  },

  /**
   * Update temp data during onboarding
   */
  updateTempData(phone, data) {
    const session = this.getOrCreateSession(phone);
    session.tempData = { ...session.tempData, ...data };
    this.saveSession(phone, session);
    return session;
  },

  /**
   * Advance to next onboarding step
   */
  nextStep(phone) {
    const steps = ['start', 'language', 'platform', 'shift', 'upi', 'pincode', 'plan', 'complete'];
    const session = this.getOrCreateSession(phone);
    const currentIndex = steps.indexOf(session.onboardingStep);
    const nextStep = steps[currentIndex + 1] || 'complete';

    return this.updateSession(phone, { onboardingStep: nextStep });
  },

  /**
   * Set language for session
   */
  setLanguage(phone, language) {
    const validLanguages = ['en', 'kn', 'hi', 'ta', 'te'];
    const lang = validLanguages.includes(language) ? language : 'en';
    return this.updateSession(phone, { language: lang });
  },

  /**
   * Mark session as completed onboarding
   */
  completeOnboarding(phone, workerData) {
    return this.updateSession(phone, {
      onboardingStep: 'complete',
      isOnboarded: true,
      workerData, // Store worker profile from backend
    });
  },

  /**
   * Add user to users database (called when worker is created in backend)
   */
  registerWorker(phone, workerData) {
    const users = this.getAllUsers();
    users[phone] = {
      ...workerData,
      registeredAt: new Date().toISOString(),
      phone,
    };
    fs.writeFileSync(USERS_DB, JSON.stringify(users, null, 2));
  },

  /**
   * Get all users
   */
  getAllUsers() {
    ensureDir(path.dirname(USERS_DB));
    if (!fs.existsSync(USERS_DB)) {
      fs.writeFileSync(USERS_DB, JSON.stringify({}));
    }
    const data = fs.readFileSync(USERS_DB, 'utf-8');
    return JSON.parse(data);
  },

  /**
   * Get user by phone
   */
  getUser(phone) {
    const users = this.getAllUsers();
    return users[phone] || null;
  },

  /**
   * Clear session (logout)
   */
  clearSession(phone) {
    const sessionFile = path.join(SESSIONS_DIR, `${phone}.json`);
    if (fs.existsSync(sessionFile)) {
      fs.unlinkSync(sessionFile);
    }
  },

  /**
   * Get all active sessions
   */
  getAllSessions() {
    ensureDir(SESSIONS_DIR);
    const files = fs.readdirSync(SESSIONS_DIR);
    const sessions = {};

    files.forEach((file) => {
      if (file.endsWith('.json')) {
        const phone = file.replace('.json', '');
        const data = fs.readFileSync(path.join(SESSIONS_DIR, file), 'utf-8');
        sessions[phone] = JSON.parse(data);
      }
    });

    return sessions;
  },
};

export default SessionManager;
