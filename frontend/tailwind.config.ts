import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: "#1e293b", dark: "#334155" },
      },
    },
  },
  plugins: [],
};

export default config;
