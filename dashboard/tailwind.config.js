/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'oao-purple': '#6d28d9',
        'oao-dark': '#0f172a',
      }
    },
  },
  plugins: [],
}
