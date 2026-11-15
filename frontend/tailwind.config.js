/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Azul noche y tonos cálidos inspirados en el logo de PyroChronos.
        ink: '#111b2d',
        panel: '#1b2940',
        panelHi: '#26364e',
        line: '#48556a',
        fire: '#ff7927',
        ember: '#ffd166',
        mist: '#ded9d0',
      },
      fontFamily: {
        sans: ['Inter', 'Geist', 'system-ui', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      boxShadow: {
        soft: '0 1px 2px rgba(0,0,0,.4), 0 12px 32px -12px rgba(0,0,0,.8)',
      },
      transitionTimingFunction: {
        smooth: 'cubic-bezier(.22,.61,.36,1)',
      },
    },
  },
  plugins: [],
}
