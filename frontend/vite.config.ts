import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
    hmr: {
      overlay: false,
    },
    proxy: {
      '/chat': 'http://localhost:8000',
      '/predict': 'http://localhost:8000',
      '/commentary': 'http://localhost:8000',
      '/articles': 'http://localhost:8000',
      '/recommendations': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
  plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
