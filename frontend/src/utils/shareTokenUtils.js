/**
 * Share Token Utilities
 * Generate and manage shareable links for worker profiles via WhatsApp
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Generate a share token for a worker
 * @param {string} workerId - UUID of the worker
 * @param {number} expiresInDays - Days until token expires (default: 30)
 * @param {number} maxUses - Maximum uses (null = unlimited)
 * @param {string} reason - Why token is being generated (default: 'dashboard')
 * @returns {Promise<string>} Share URL
 */
export const generateShareToken = async (workerId, expiresInDays = 30, maxUses = null, reason = 'dashboard') => {
  try {
    console.log(`[SHARE] Generating token for worker: ${workerId}`);

    const response = await fetch(`${API_BASE_URL}/api/v1/share-tokens/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        worker_id: workerId,
        expires_in_days: expiresInDays,
        max_uses: maxUses,
        reason: reason,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    console.log(`[SHARE] Token generated successfully: ${data.share_url}`);
    return data.share_url;
  } catch (error) {
    console.error('[SHARE] Error generating token:', error);
    throw error;
  }
};

/**
 * Verify a share token is valid
 * @param {string} token - Share token to verify
 * @returns {Promise<Object>} Verification result
 */
export const verifyShareToken = async (token) => {
  try {
    console.log(`[SHARE] Verifying token: ${token.substring(0, 8)}...`);

    const response = await fetch(`${API_BASE_URL}/api/v1/share-tokens/verify/${token}`);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: Token verification failed`);
    }

    const data = await response.json();
    console.log(`[SHARE] Verification result:`, data);
    return data;
  } catch (error) {
    console.error('[SHARE] Error verifying token:', error);
    throw error;
  }
};

/**
 * Get shared worker profile by token
 * @param {string} token - Share token
 * @returns {Promise<Object>} Worker public profile data
 */
export const getSharedWorkerProfile = async (token) => {
  try {
    console.log(`[SHARE] Fetching profile for token: ${token.substring(0, 8)}...`);

    const response = await fetch(`${API_BASE_URL}/api/v1/share-tokens/profile/${token}`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch worker profile');
    }

    const data = await response.json();
    console.log(`[SHARE] Profile fetched for worker: ${data.id}`);
    return data;
  } catch (error) {
    console.error('[SHARE] Error fetching profile:', error);
    throw error;
  }
};

/**
 * Copy text to clipboard with fallback
 * @param {string} text - Text to copy
 * @returns {Promise<boolean>} Success status
 */
export const copyToClipboard = async (text) => {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      console.log('[SHARE] Copied to clipboard (modern API)');
      return true;
    } else {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      const success = document.execCommand('copy');
      document.body.removeChild(textarea);
      console.log(`[SHARE] Copied to clipboard (fallback): ${success}`);
      return success;
    }
  } catch (error) {
    console.error('[SHARE] Error copying to clipboard:', error);
    return false;
  }
};

/**
 * Share link on WhatsApp
 * @param {string} link - Share URL
 * @param {string} workerName - Worker name for context
 */
export const shareOnWhatsApp = (link, workerName) => {
  try {
    const message = `Check out ${workerName}'s profile: ${link}`;
    const encodedMessage = encodeURIComponent(message);
    const whatsappUrl = `https://wa.me/?text=${encodedMessage}`;
    
    console.log('[SHARE] Opening WhatsApp with link');
    window.open(whatsappUrl, '_blank');
  } catch (error) {
    console.error('[SHARE] Error sharing on WhatsApp:', error);
    throw error;
  }
};
