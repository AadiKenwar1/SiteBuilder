/** @type {import('tailwindcss').Config} */
// Tailwind powers the owner admin UI (and shared chrome). Per-business public
// designs bring their own CSS in designs/<slug>/styles.css.
module.exports = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./designs/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: { extend: {} },
  plugins: [],
}
