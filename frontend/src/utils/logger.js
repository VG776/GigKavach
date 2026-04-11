/**
 * Frontend Logger Utility
 * Centralizes logging with DEBUG mode control
 * In production, DEBUG_MODE = false to reduce console noise
 */

const DEBUG_MODE = import.meta.env.VITE_DEBUG_MODE === 'true' || false;

export const logger = {
  debug: (module, message, data = null) => {
    if (DEBUG_MODE) {
      console.log(`[${module}] ${message}`, data || '');
    }
  },

  info: (module, message, data = null) => {
    console.log(`[${module}] ${message}`, data || '');
  },

  warn: (module, message, data = null) => {
    console.warn(`[${module}] ${message}`, data || '');
  },

  error: (module, message, data = null) => {
    console.error(`[${module}] ${message}`, data || '');
  }
};
