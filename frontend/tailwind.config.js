/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{html,ts,scss}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Outfit"', 'system-ui', '-apple-system', 'sans-serif'],
      },
      colors: {
        primary: 'var(--color-primary)',
        secondary: 'var(--color-secondary)',
        accent: 'var(--color-accent)',
        surface: 'var(--color-surface)',
        muted: 'var(--color-muted)',
        success: 'var(--color-success)',
        warning: 'var(--color-warning)',
        danger: 'var(--color-danger)',
      },
      borderRadius: {
        brand: 'var(--radius-brand)',
        pill: 'var(--radius-pill)',
      },
      boxShadow: {
        brand: 'var(--shadow-brand)',
      },
    },
  },
  plugins: [],
};
