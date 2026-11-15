/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Negro carbón, naranja, amarillo y crema del logo.
        ink: '#13110f',
        panel: '#24201c',
        panelHi: '#332b24',
        line: '#625343',
        fire: '#ff7927',
        ember: '#ffd166',
        mist: '#f0e1cc',
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
