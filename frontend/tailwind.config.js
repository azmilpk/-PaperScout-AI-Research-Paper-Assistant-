/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        lime: {
          DEFAULT: '#CFFF74',
          hover: '#d8ff8a',
          soft: 'rgba(207, 255, 116, 0.15)',
          glow: 'rgba(207, 255, 116, 0.35)',
        },
        olive: {
          DEFAULT: '#2F3A1D',
          dark: '#141c12',
          panel: '#1b2618',
          card: '#222f1e',
          border: 'rgba(207, 255, 116, 0.2)',
        },
        brand: {
          DEFAULT: '#CFFF74',
          hover: '#d8ff8a',
          dark: '#141c12',
        }
      },
      fontFamily: {
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'lime-glow': '0 0 24px rgba(207, 255, 116, 0.35)',
      }
    },
  },
  plugins: [],
}
