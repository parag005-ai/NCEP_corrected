import forms from "@tailwindcss/forms";
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#f7faf8",
        "surface-dim": "#d7dbd9",
        "surface-bright": "#f7faf8",
        "surface-panel": "#FCFDFD",
        "surface-container-lowest": "#ffffff",
        "surface-container-low": "#f1f4f3",
        "surface-container": "#ebefed",
        "surface-container-high": "#e5e9e7",
        "surface-container-highest": "#e0e3e1",
        "surface-variant": "#e0e3e1",
        "on-surface": "#181c1c",
        "on-surface-variant": "#3e4947",
        outline: "#6e7977",
        "outline-variant": "#bdc9c6",
        primary: "#005c55",
        "primary-container": "#0f766e",
        "on-primary": "#ffffff",
        "on-primary-container": "#a3faef",
        "surface-tint": "#006a63",
        secondary: "#4c6360",
        "secondary-container": "#cfe8e4",
        "border-muted": "#D9E5E8",
        "medical-cyan": "#2CB5A5",
        success: "#10B981",
        warning: "#F59E0B",
        critical: "#EF4444",
        info: "#3B82F6"
      },
      borderRadius: {
        sm: "0.25rem",
        DEFAULT: "0.5rem",
        md: "0.75rem",
        lg: "1rem",
        xl: "1.5rem",
        "2xl": "20px"
      },
      spacing: {
        "container-max": "1200px",
        gutter: "24px",
        "margin-mobile": "16px",
        "header-height": "72px",
        "input-height": "52px"
      },
      fontSize: {
        hero: ["48px", { lineHeight: "1.2", fontWeight: "600" }],
        "headline-lg": ["36px", { lineHeight: "1.2", fontWeight: "600" }],
        "section-title": ["28px", { lineHeight: "1.3", fontWeight: "600" }],
        "card-title": ["22px", { lineHeight: "1.4", fontWeight: "500" }],
        "body-lg": ["16px", { lineHeight: "1.6", fontWeight: "400" }],
        "body-sm": ["14px", { lineHeight: "1.5", fontWeight: "400" }],
        caption: ["12px", { lineHeight: "1.4", fontWeight: "500", letterSpacing: "0.05em" }]
      },
      boxShadow: {
        ambient: "0 12px 48px -12px rgba(0, 92, 85, 0.08)",
        panel: "0 18px 55px -30px rgba(0, 92, 85, 0.24)"
      },
      keyframes: {
        drawEcg: {
          "0%": { strokeDashoffset: "1000" },
          "50%": { strokeDashoffset: "0" },
          "100%": { strokeDashoffset: "-1000" }
        }
      },
      animation: {
        "draw-ecg": "drawEcg 8s linear infinite"
      }
    }
  },
  plugins: [forms]
};

export default config;
