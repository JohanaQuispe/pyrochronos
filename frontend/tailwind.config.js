/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#070b14',
        panel: '#0f172a',
        panelHi: '#16213a',
        line: '#243354',
        fire: '#ff8a3d',
        ember: '#ffb703',
        mist: '#a8b6cf',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
