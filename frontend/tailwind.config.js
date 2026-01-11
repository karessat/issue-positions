/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        democrat: '#3B82F6',
        republican: '#EF4444',
        independent: '#8B5CF6',
      },
    },
  },
  plugins: [],
}
