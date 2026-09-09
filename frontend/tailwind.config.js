/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'border-red':   '#ef4444',
        'border-amber': '#f59e0b',
        'border-gray':  '#6b7280',
        'panel':        '#1e293b',
        'panel-dark':   '#0f172a',
      },
    },
  },
  plugins: [],
}
