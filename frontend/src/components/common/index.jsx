import React from 'react';

/**
 * Badge component for status indicators
 */
export const Badge = ({ children, variant = 'default', className = '', ...props }) => {
  const variantStyles = {
    default: 'bg-gray-200 text-gray-900 dark:bg-gray-700 dark:text-gray-100',
    success: 'bg-green-100 text-green-900 dark:bg-green-900 dark:text-green-100',
    warning: 'bg-amber-100 text-amber-900 dark:bg-amber-900 dark:text-amber-100',
    danger: 'bg-red-100 text-red-900 dark:bg-red-900 dark:text-red-100',
    info: 'bg-blue-100 text-blue-900 dark:bg-blue-900 dark:text-blue-100',
    primary: 'bg-gigkavach-orange text-white',
  };

  return (
    <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${variantStyles[variant]} ${className}`} {...props}>
      {children}
    </span>
  );
};

/**
 * Loading Spinner component
 */
export const LoadingSpinner = ({ size = 'md', className = '' }) => {
  const sizeStyles = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  return (
    <div className={`animate-spin rounded-full border-4 border-gray-300 border-t-gigkavach-orange dark:border-gray-600 dark:border-t-gigkavach-orange ${sizeStyles[size]} ${className}`} />
  );
};

/**
 * Toast notification component
 */
export const Toast = ({ message, variant = 'info', onClose, autoClose = true, duration = 4000 }) => {
  React.useEffect(() => {
    if (autoClose && duration > 0) {
      const timer = setTimeout(onClose, duration);
      return () => clearTimeout(timer);
    }
  }, [autoClose, duration, onClose]);

  const variantStyles = {
    info: 'bg-blue-500 text-white',
    success: 'bg-green-500 text-white',
    warning: 'bg-amber-500 text-white',
    error: 'bg-red-500 text-white',
  };

  return (
    <div className={`fixed bottom-4 right-4 px-4 py-3 rounded-lg ${variantStyles[variant]} shadow-lg animate-slide-up`}>
      {message}
    </div>
  );
};

/**
 * Modal/Dialog component
 */
export const Modal = ({ isOpen, title, onClose, children, actions, size = 'md' }) => {
  if (!isOpen) return null;

  const sizeStyles = {
    sm: 'w-full max-w-sm',
    md: 'w-full max-w-md',
    lg: 'w-full max-w-lg',
    xl: 'w-full max-w-2xl',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className={`bg-white dark:bg-gigkavach-surface rounded-lg shadow-2xl ${sizeStyles[size]} max-h-[90vh] overflow-y-auto`}>
        {/* Header */}
        <div className="flex items-center justify-between border-b dark:border-gray-700 p-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">{title}</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-2xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6">{children}</div>

        {/* Footer */}
        {actions && (
          <div className="flex gap-3 justify-end border-t dark:border-gray-700 p-6 bg-gray-50 dark:bg-gray-800">
            {actions}
          </div>
        )}
      </div>
    </div>
  );
};
