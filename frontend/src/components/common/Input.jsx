import React from 'react';

/**
 * Reusable Input component
 */
export const Input = React.forwardRef(
  ({ type = 'text', size = 'md', error = false, className = '', ...props }, ref) => {
    const baseStyles = 'border rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-gigkavach-orange';

    const sizeStyles = {
      sm: 'px-2 py-1 text-sm',
      md: 'px-3 py-2 text-base',
      lg: 'px-4 py-3 text-lg',
    };

    const stateStyles = error
      ? 'border-red-500 dark:border-red-400'
      : 'border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100';

    return (
      <input
        ref={ref}
        type={type}
        className={`${baseStyles} ${sizeStyles[size]} ${stateStyles} ${className}`}
        {...props}
      />
    );
  }
);

Input.displayName = 'Input';
