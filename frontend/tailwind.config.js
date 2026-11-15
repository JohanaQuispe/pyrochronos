/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Superficies de pizarra más claras para diferenciar secciones y controles.
        ink: '#1b2939',
        panel: '#233449',
        panelHi: '#30445b',
        line: '#50657a',
        // El fuego es el único color con permiso para llamar la atención.
        fire: '#f97316',
        ember: '#fbbf24',
        mist: '#a1a1aa',
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
