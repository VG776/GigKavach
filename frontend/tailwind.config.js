/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // GigKavach Brand Colors
        gigkavach: {
          'navy': '#0F1B2D',           // Primary brand - backgrounds, sidebar
          'navy-light': '#162236',     // Lighter navy for gradients
          'orange': '#FF6B35',         // Accent - CTAs, urgency, alerts
          'green': '#22C55E',          // Safe green - paid, low risk
          'amber': '#F59E0B',          // Warning amber - pending, medium risk
          'red': '#EF4444',            // Danger red - fraud, catastrophic
          'surface': '#1A2942',        // Card surfaces on dark bg
          'slate': '#1F2937',          // Secondary surface
        },
      },
      fontFamily: {
        display: ['"DM Sans"', '"Plus Jakarta Sans"', 'sans-serif'],
        body: ['"DM Sans"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      animation: {
        'pulse-fast': 'pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite',
      },
      keyframes: {
        glow: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
      },
      boxShadow: {
        'card': '0 1px 3px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.04)',
        'card-hover': '0 4px 6px rgba(0, 0, 0, 0.12), 0 2px 4px rgba(0, 0, 0, 0.06)',
      },
    },
  },
  plugins: [],
};
