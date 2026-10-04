/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Brand palette
        marigold: { DEFAULT: "#E59D2C", 50: "#FDF5E7", 100: "#FAE8C7", 200: "#F4D092", 300: "#EDB85C", 400: "#E9AA43", 500: "#E59D2C", 600: "#C9831A", 700: "#A26815", 800: "#7B4F10", 900: "#54360B" },
        buff: { DEFAULT: "#F3D58D", 50: "#FEFAF0", 100: "#FCF2D9", 200: "#F9E8B8", 300: "#F6DE9F", 400: "#F3D58D", 500: "#EDC360", 600: "#E4AD2C", 700: "#B8871A" },
        pearl: { DEFAULT: "#EBDDC5", 50: "#FBF8F2", 100: "#F7F1E6", 200: "#F1E7D6", 300: "#EBDDC5", 400: "#DCC7A3", 500: "#CCB081", 600: "#B3925C" },
        police: { DEFAULT: "#2E4365", 50: "#EEF1F6", 100: "#D6DDE8", 200: "#AEBBD1", 300: "#8196B6", 400: "#5A7196", 500: "#3F5A83", 600: "#2E4365", 700: "#253652", 800: "#1C2940", 900: "#131C2C" },
        citrine: { DEFAULT: "#8A3B08", 50: "#FBEFE6", 100: "#F4D6C1", 200: "#E6A983", 300: "#D27A48", 400: "#B45A1E", 500: "#8A3B08", 600: "#723107", 700: "#592605", 800: "#401B04" },
        ink: "#1F2D45",
        muted: "#5E6B80",
        paper: "#FCFAF6",
        line: "#E3D5BD",
      },
      fontFamily: {
        display: ['"DM Serif Display"', "Georgia", "serif"],
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        mono: ['"JetBrains Mono"', "Menlo", "Consolas", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(46,67,101,0.06), 0 4px 16px rgba(46,67,101,0.06)",
      },
    },
  },
  plugins: [],
};
