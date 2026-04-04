/**
 * utils/validators.js
 * ─────────────────────────────────────────
 * Validation utilities for user inputs
 */

/**
 * Validate UPI ID format
 * Format: identifier@bankname or identifier@upi
 */
export function validateUPI(upi) {
  const upiRegex = /^[a-zA-Z0-9._-]+@[a-zA-Z]{3,}$/;
  return upiRegex.test(upi);
}

/**
 * Validate PIN code (6 digits)
 */
export function validatePincode(pincode) {
  return /^\d{6}$/.test(pincode);
}

/**
 * Validate phone number (10 digits)
 */
export function validatePhone(phone) {
  return /^\d{10}$/.test(phone);
}

/**
 * Validate multiple pin codes (comma-separated, max 5)
 */
export function validatePincodes(pincodeString) {
  const pincodes = pincodeString
    .split(',')
    .map((p) => p.trim())
    .filter((p) => p.length > 0);

  if (pincodes.length === 0 || pincodes.length > 5) {
    return { valid: false, error: 'Provide 1-5 pin codes' };
  }

  const allValid = pincodes.every(validatePincode);
  if (!allValid) {
    return { valid: false, error: 'All pin codes must be 6 digits' };
  }

  return { valid: true, pincodes };
}

/**
 * Validate plan selection
 */
export function validatePlan(plan) {
  const validPlans = ['Shield Basic', 'Shield Plus', 'Shield Pro', 'basic', 'plus', 'pro'];
  return validPlans.includes(plan.toLowerCase());
}

/**
 * Validate platform selection
 */
export function validatePlatform(platform) {
  const validPlatforms = ['Zomato', 'Swiggy', 'zomato', 'swiggy'];
  return validPlatforms.includes(platform.toLowerCase());
}

/**
 * Validate shift selection
 */
export function validateShift(shift) {
  const validShifts = [
    'Morning (6AM–2PM)',
    'Day (9AM–9PM)',
    'Night (6PM–2AM)',
    'Flexible',
    'morning',
    'day',
    'night',
    'flexible',
  ];
  return validShifts.some((s) => s.toLowerCase() === shift.toLowerCase());
}
