/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Institutional RWA - Automotive Fintech Palette
        bg: {
          primary: "#F8FAFC",
          secondary: "#F1F5F9",
          card: "#FFFFFF",
        },
        dark: {
          900: "#0F172A",
          800: "#1E293B",
          700: "#334155",
        },
        gray: {
          100: "#F8FAFC",
          200: "#E2E8F0",
          300: "#CBD5E1",
          400: "#94A3B8",
          500: "#64748B",
          600: "#475569",
          700: "#334155",
          800: "#1E293B",
          900: "#0F172A",
        },
        emerald: {
          50: "#ECFDF5",
          400: "#34D399",
          500: "#10B981",
          600: "#059669",
        },
        blue: {
          50: "#EFF6FF",
          400: "#60A5FA",
          500: "#2563EB",
          600: "#1D4ED8",
          700: "#1E40AF",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        sm: "4px",
        md: "8px",
        lg: "12px",
        xl: "16px",
      },
    },
  },
  plugins: [require("@tailwindcss/forms")],
};
