import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: ['class'],
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Aurora Solar Light Theme
        aurora: {
          // Primary colors
          gold: '#FFD700',
          cyan: '#00CED1',
          purple: '#9370DB',
          orange: '#FFA500',
          pink: '#FF69B4',

          // Neutrals
          white: '#F8F9FB',
          light: '#E0F7FF',
          'soft-gold': '#FFF8DC',

          // Text
          'deep-blue': '#001a4d',

          // Success/Status
          green: '#4DBD33',
        },

        // Semantic aliases
        background: '#F8F9FB',
        foreground: '#001a4d',
        primary: {
          DEFAULT: '#FFD700',
          foreground: '#001a4d',
        },
        secondary: {
          DEFAULT: '#00CED1',
          foreground: '#001a4d',
        },
        accent: {
          DEFAULT: '#9370DB',
          foreground: '#FFFFFF',
        },
        muted: {
          DEFAULT: '#E0F7FF',
          foreground: '#001a4d',
        },
        card: {
          DEFAULT: 'rgba(255, 255, 255, 0.85)',
          foreground: '#001a4d',
        },
        border: 'rgba(0, 206, 209, 0.3)',
      },

      backgroundImage: {
        // Aurora gradients
        'aurora-gradient': 'linear-gradient(135deg, #FFD700 0%, #00CED1 50%, #9370DB 100%)',
        'aurora-subtle': 'linear-gradient(135deg, rgba(255, 215, 0, 0.15) 0%, rgba(0, 206, 209, 0.15) 50%, rgba(147, 112, 219, 0.15) 100%)',
        'sunrise-gradient': 'linear-gradient(135deg, #FFA500 0%, #FFD700 50%, #00CED1 100%)',
      },

      boxShadow: {
        'aurora': '0 8px 32px rgba(0, 206, 209, 0.15)',
        'aurora-lg': '0 12px 48px rgba(0, 206, 209, 0.2)',
        'gold': '0 4px 16px rgba(255, 215, 0, 0.3)',
      },

      borderRadius: {
        lg: '16px',
        md: '12px',
        sm: '8px',
      },

      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },

      animation: {
        'aurora-flow': 'aurora-flow 8s ease-in-out infinite',
        'fade-in': 'fade-in 0.3s ease-out',
        'slide-up': 'slide-up 0.4s ease-out',
      },

      keyframes: {
        'aurora-flow': {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'slide-up': {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}

export default config
