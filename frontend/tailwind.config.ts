import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#172033",
        canvas: "#f6f7fb",
        brand: {
          DEFAULT: "#5850ec",
          dark: "#4338ca",
        },
      },
      boxShadow: {
        panel: "0 20px 60px -30px rgba(23, 32, 51, 0.35)",
      },
    },
  },
  plugins: [],
};

export default config;
