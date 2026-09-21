/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: [
          "'Space Grotesk'",
          "system-ui",
          "sans-serif",
        ],
        serif: [
          "'Newsreader'",
          "Georgia",
          "'Times New Roman'",
          "serif",
        ],
        mono: [
          "'JetBrains Mono'",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "monospace",
        ],
      },
      colors: {
        fn: {
          void: "#09090B",
          surface: "#18181B",
          elevated: "#27272A",
          border: "#3F3F46",
          "border-focus": "#71717A",
          "text-primary": "#FAFAFA",
          "text-secondary": "#A1A1AA",
          "text-tertiary": "#71717A",
          proof: "#F59E0B",
          "proof-muted": "#D97706",
          "proof-subtle": "rgba(245, 158, 11, 0.12)",
          "proof-bg": "#78350F",
          verified: "#34D399",
          inferred: "#A1A1AA",
          flagged: "#FB7185",
        },
      },
      animation: {
        "fade-in-up": "fade-in-up 0.3s ease-out both",
        "pulse-amber": "pulse-amber 2s ease-in-out infinite",
      },
      keyframes: {
        "fade-in-up": {
          from: { opacity: "0", transform: "translateY(12px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "pulse-amber": {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(245, 158, 11, 0.4)" },
          "50%": { boxShadow: "0 0 0 6px rgba(245, 158, 11, 0)" },
        },
      },
    },
  },
  plugins: [],
};
