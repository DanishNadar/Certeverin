import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./charts/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#10233f",
        panel: "#f8fafc",
        accent: "#0f766e",
        gold: "#b45309"
      }
    }
  },
  plugins: []
};

export default config;
