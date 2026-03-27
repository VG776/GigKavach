/**
 * Client-side form validation
 */

export const validators = {
  /**
   * Validate email format
   */
  email: (email) => {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
  },

  /**
   * Validate phone number
   */
  phone: (phone) => {
    const cleaned = phone.replace(/\D/g, '');
    return cleaned.length === 10;
  },

  /**
   * Validate DCI value (0-100)
   */
  dciValue: (value) => {
    const num = parseInt(value);
    return !isNaN(num) && num >= 0 && num <= 100;
  },

  /**
   * Validate coverage percentage (0-100)
   */
  coveragePercentage: (value) => {
    const num = parseInt(value);
    return !isNaN(num) && num >= 0 && num <= 100;
  },

  /**
   * Validate amount (positive number)
   */
  amount: (value) => {
    const num = parseFloat(value);
    return !isNaN(num) && num > 0;
  },

  /**
   * Validate required field
   */
  required: (value) => {
    return value !== null && value !== undefined && value.toString().trim() !== '';
  },

  /**
   * Validate minimum length
   */
  minLength: (value, length) => {
    return value && value.toString().length >= length;
  },

  /**
   * Validate maximum length
   */
  maxLength: (value, length) => {
    return !value || value.toString().length <= length;
  },

  /**
   * Validate password strength
   */
  passwordStrength: (password) => {
    if (!password || password.length < 8) return false;
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasNumbers = /\d/.test(password);
    const hasSpecialChar = /[!@#$%^&*]/.test(password);
    return hasUpperCase && hasLowerCase && hasNumbers && hasSpecialChar;
  },
};

/**
 * Validate form data object
 */
export const validateForm = (data, schema) => {
  const errors = {};
  Object.keys(schema).forEach((field) => {
    const rules = schema[field];
    const value = data[field];
    if (Array.isArray(rules)) {
      for (const rule of rules) {
        const isValid = typeof rule === 'function' ? rule(value) : true;
        if (!isValid) {
          errors[field] = `${field} is invalid`;
          break;
        }
      }
    }
  });
  return errors;
};
