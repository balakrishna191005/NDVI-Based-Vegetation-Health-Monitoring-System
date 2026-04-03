import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/get-ndvi": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/get-ndvi/latest": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/get-timeseries": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/get-analysis": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/download-report": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/health": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/sample-ndvi-point": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
