import React from 'react';

/**
 * Reusable Button component with variants
 */
export const Button = React.forwardRef(
  (
    {
      children,
      variant = 'primary',
      size = 'md',
      disabled = false,
      loading = false,
      className = '',
      ...props
    },
    ref
  ) => {
    const baseStyles = 'font-medium rounded-md transition-colors inline-flex items-center justify-center whitespace-nowrap';

    const variantStyles = {
      primary: 'bg-gigkavach-orange text-white hover:bg-orange-600 disabled:bg-gray-400',
      secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-100',
      outline: 'border border-gray-300 text-gray-900 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-100 dark:hover:bg-gray-800',
      danger: 'bg-red-600 text-white hover:bg-red-700 disabled:bg-gray-400',
      ghost: 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800',
    };

    const sizeStyles = {
      sm: 'px-2 py-1 text-sm gap-1',
      md: 'px-4 py-2 text-base gap-2',
      lg: 'px-6 py-3 text-lg gap-2',
    };

    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
        {...props}
      >
        {loading && <span className="animate-spin mr-2">⏳</span>}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
