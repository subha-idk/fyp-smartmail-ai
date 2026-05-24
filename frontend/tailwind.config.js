/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      colors: {
        navy: {
          950: "#0a0f1e",
          900: "#080d1a",
          800: "#0f1729",
          750: "#0d1526",
        },
        indigo: {
          // keep Tailwind defaults; add aliases for design tokens
        },
      },
      backgroundImage: {
        "indigo-gradient": "linear-gradient(135deg, #6366f1, #8b5cf6)",
        "glass-surface":
          "linear-gradient(135deg, rgba(15,23,41,0.9) 0%, rgba(10,15,30,0.7) 100%)",
      },
      boxShadow: {
        glass: "0 4px 24px rgba(0,0,0,0.4)",
        "glass-lg": "0 8px 32px rgba(0,0,0,0.55)",
        "glass-inset": "inset 0 1px 0 rgba(255,255,255,0.05)",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        shimmer: "shimmer 1.5s infinite",
        "slide-in-left": "slideInLeft 0.2s ease",
        "fade-in": "fadeIn 0.3s ease",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" },
        },
        slideInLeft: {
          from: { transform: "translateX(-100%)" },
          to: { transform: "translateX(0)" },
        },
        fadeIn: {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
