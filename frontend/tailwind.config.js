/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Geist",
          "-apple-system",
          "BlinkMacSystemFont",
          '"Segoe UI"',
          "Roboto",
          "sans-serif",
        ],
        mono: [
          "GeistMono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "monospace",
        ],
      },
      colors: {
        vercel: {
          bg: "#000000",
          card: "#0A0A0A",
          cardHover: "#121212",
          cardActive: "#171717",
          border: "#262626",
          borderHover: "#404040",
          textMuted: "#A1A1AA",
          textSubtle: "#71717A",
          accent: "#FFFFFF",
          emerald: "#10B981",
          amber: "#F59E0B",
          rose: "#F43F5E",
          blue: "#38BDF8",
        },
      },
    },
  },
  plugins: [],
};
