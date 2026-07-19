import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        fg: "var(--fg)",
        card: "var(--card)",
        line: "var(--line)",
        accent: "var(--accent)"
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.4rem"
      },
      boxShadow: {
        soft: "0 8px 40px rgba(15, 64, 153, 0.08)"
      }
    }
  },
  plugins: []
};

export default config;
