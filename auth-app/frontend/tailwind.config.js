/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Reading-focused design system colors
        reading: {
          // Paper-like backgrounds
          background: '#F3EDE3',     // Main page background - warm paper tone
          section: '#F5F1E8',       // Section backgrounds
          card: '#ECE5D4',          // Card backgrounds
          
          // Subtle borders and separators
          border: '#DDD2BD',        // Minimal borders and dividers
          
          // Accent colors
          accent: '#A88C64',        // Border accents for section titles
          
          // Scrollbar colors
          scrollThumb: '#BFAE8F',   // Scrollbar thumb
          scrollTrack: '#F3EDE3',   // Scrollbar track
          
          // Hover states
          hover: '#eae0c6',         // Subtle hover background tint
          
          // Text colors
          text: {
            primary: '#231F20',     // Primary text
            secondary: '#4A4A4A',   // Secondary text
            muted: '#6B6B6B',       // Muted text
          }
        },
        
        // Goodreads-inspired color scheme (legacy support)
        brand: {
          primary: '#553B08',       // Main logo, navigation, CTA buttons
          hover: '#75420E',         // Hover states, focus indicators
        },
        goodreads: {
          cream: '#E9E5CD',         // Sidebar backgrounds, recommendation cards
          white: '#FFFFFF',         // Clean base background
          background: '#F5F0E1',    // Main page background - warm beige
          border: '#AAAAAA',        // Subtle borders, placeholders
          text: '#231F20',          // Primary typography
        },
        
        // Legacy colors for gradual migration
        legacy: {
          amber: {
            700: '#b45309',
            800: '#92400e',
            900: '#78350f',
          }
        }
      },
      fontFamily: {
        'reading': ['Inter', 'system-ui', 'sans-serif'],
        'goodreads': ['Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'reading-base': ['1.25rem', { lineHeight: '1.75rem', letterSpacing: '-0.2px' }],
        'reading-sm': ['1.125rem', { lineHeight: '1.625rem', letterSpacing: '-0.1px' }],
        'reading-lg': ['1.375rem', { lineHeight: '1.875rem', letterSpacing: '-0.3px' }],
      },
      fontWeight: {
        'reading': '500',
      },
      spacing: {
        'reading': '0.5rem',
      },
      boxShadow: {
        'reading-subtle': '0 1px 2px rgba(0, 0, 0, 0.05)',
        'reading-soft': 'inset 0 1px 2px rgba(0, 0, 0, 0.05)',
        'goodreads': '0 2px 8px rgba(85, 59, 8, 0.1)',
        'goodreads-hover': '0 4px 16px rgba(85, 59, 8, 0.15)',
      },
      backgroundImage: {
        'reading-gradient': 'linear-gradient(135deg, #F5F1E8 0%, #ECE5D4 100%)',
      }
    },
  },
  screens: {
    'xs': '475px',
    'sm': '640px',
    'md': '768px',
    'lg': '1024px',
    'xl': '1280px',
    '2xl': '1536px',
  },
  plugins: [],
}
