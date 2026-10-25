import { defineConfig } from "vite";
export default defineConfig({ base: "./", server: { host: "127.0.0.1", port: 1420, strictPort: true }, build: { outDir: "dist", sourcemap: false, emptyOutDir: true, rollupOptions: { output: { manualChunks: { "react-vendor": ["react", "react-dom", "react-dom/client"] } } } } });
