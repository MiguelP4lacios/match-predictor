/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)',
        surface: 'var(--bg-elevated)',
        text: 'var(--fg)',
        'text-muted': 'var(--fg-muted)',
        border: 'var(--border)',
        primary: 'var(--primary)',
        'primary-fg': 'var(--primary-fg)',
        success: 'var(--success)',
        warn: 'var(--warn)',
        danger: 'var(--danger)',
        qualify: 'var(--qualify)',
      },
    },
  },
  plugins: [],
}
