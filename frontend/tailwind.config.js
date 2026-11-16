/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#070d16",
          900: "#0b1422",
          850: "#101c2e",
          800: "#15243a",
          700: "#1e3350",
          600: "#2a466b",
        },
        pulse: {
          DEFAULT: "#3b82f6",
          soft: "#60a5fa",
          teal: "#2dd4bf",
          amber: "#f59e0b",
          rose: "#fb7185",
          green: "#34d399",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        card: "0 18px 45px -30px rgba(2, 8, 23, 0.9)",
      },
    },
  },
  plugins: [],
};
