import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Built output goes to web/dist, which serve.py hands out. During development
// `npm run dev` proxies /api to the Python server on 8000 so there is only
// ever one source of truth for the data.
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "dist",
    emptyOutDir: true,
    // Everything inlined where possible so the built demo has no surprises
    // about asset paths when served from the stdlib http.server.
    assetsInlineLimit: 8192,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: false,
      },
    },
  },
});
