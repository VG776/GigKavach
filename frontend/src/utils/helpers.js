/**
 * Miscellaneous helper functions
 */

/**
 * Delay execution for specified milliseconds
 */
export const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Retry function with exponential backoff
 */
export const retryWithBackoff = async (fn, maxAttempts = 3, delay = 1000) => {
  let lastError;
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      if (attempt < maxAttempts - 1) {
        const waitTime = delay * Math.pow(2, attempt);
        await new Promise((resolve) => setTimeout(resolve, waitTime));
      }
    }
  }
  throw lastError;
};

/**
 * Get DCI level based on value
 */
export const getDCILevel = (value) => {
  if (value >= 75) return 'critical';
  if (value >= 60) return 'high';
  if (value >= 40) return 'medium';
  return 'low';
};

/**
 * Get DCI color based on level
 */
export const getDCIColor = (level) => {
  const colors = {
    critical: '#7F1D1D',
    high: '#EF4444',
    medium: '#F59E0B',
    low: '#22C55E',
    excellent: '#059669',
  };
  return colors[level] || '#9CA3AF';
};

/**
 * Get risk level based on fraud score
 */
export const getRiskLevel = (score) => {
  if (score >= 5) return 'high';
  if (score >= 3) return 'medium';
  return 'low';
};

/**
 * Get risk color
 */
export const getRiskColor = (level) => {
  const colors = {
    high: '#EF4444',
    medium: '#F59E0B',
    low: '#22C55E',
  };
  return colors[level] || '#9CA3AF';
};

/**
 * Generate random ID
 */
export const generateID = () => {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

/**
 * Truncate text with ellipsis
 */
export const truncateText = (text, length = 50) => {
  if (!text) return '';
  return text.length > length ? text.substring(0, length) + '...' : text;
};

/**
 * Clone object deep
 */
export const deepClone = (obj) => {
  return JSON.parse(JSON.stringify(obj));
};

/**
 * Check if object is empty
 */
export const isEmpty = (obj) => {
  return Object.keys(obj).length === 0;
};

/**
 * Debounce function
 */
export const debounce = (func, wait) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

/**
 * Throttle function
 */
export const throttle = (func, limit) => {
  let inThrottle;
  return function (...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
};

/**
 * Group array by property
 */
export const groupBy = (array, property) => {
  return array.reduce((groups, item) => {
    const key = item[property];
    if (!groups[key]) {
      groups[key] = [];
    }
    groups[key].push(item);
    return groups;
  }, {});
};

/**
 * Sort array by property
 */
export const sortBy = (array, property, ascending = true) => {
  return [...array].sort((a, b) => {
    if (a[property] < b[property]) return ascending ? -1 : 1;
    if (a[property] > b[property]) return ascending ? 1 : -1;
    return 0;
  });
};

/**
 * Filter array by multiple conditions
 */
export const filterByMultiple = (array, filters) => {
  return array.filter((item) => {
    return Object.entries(filters).every(([key, value]) => {
      if (Array.isArray(value)) {
        return value.includes(item[key]);
      }
      return item[key] === value || item[key].toString().toLowerCase().includes(value?.toString().toLowerCase());
    });
  });
};

/**
 * Check if device is mobile
 */
export const isMobile = () => {
  return window.innerWidth < 768;
};

/**
 * Check if device is tablet
 */
export const isTablet = () => {
  return window.innerWidth >= 768 && window.innerWidth < 1024;
};

/**
 * Check if device is desktop
 */
export const isDesktop = () => {
  return window.innerWidth >= 1024;
};

/**
 * Get device type
 */
export const getDeviceType = () => {
  if (isMobile()) return 'mobile';
  if (isTablet()) return 'tablet';
  return 'desktop';
};
