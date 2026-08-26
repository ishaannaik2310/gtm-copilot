/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "Liberation Mono",
          "Courier New",
          "monospace",
        ],
      },
      colors: {
        obsidian: {
          950: "#06090F",
          900: "#0B111D",
          850: "#101827",
          800: "#172236",
          700: "#22314E",
          600: "#334568",
        },
        trust: {
          emerald: "#10B981",
          emeraldBg: "#064E3B",
          amber: "#F59E0B",
          amberBg: "#78350F",
          sky: "#38BDF8",
          skyBg: "#0C4A6E",
          rose: "#F43F5E",
          roseBg: "#881337",
        },
      },
    },
  },
  plugins: [],
};
