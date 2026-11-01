import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // static GitHub Pages build uses relative paths: VITE_BASE=./ VITE_STATIC=1 npm run build
  base: process.env.VITE_BASE ?? "/",
  server: { proxy: { "/api": "http://localhost:8000" } },
  build: { outDir: "dist", chunkSizeWarningLimit: 1200 },
});
