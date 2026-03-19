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
      '/chat': {
        target: 'http://localhost:8000',
        bypass(req) {
          // Browser navigation sends GET with text/html — let Vite serve the SPA
          if (req.headers.accept?.includes('text/html')) return req.url;
        },
      },
      '/predict/analysis': 'http://localhost:8000',
      '/predict': 'http://localhost:8000',
      '/commentary': 'http://localhost:8000',
      '/articles': 'http://localhost:8000',
      '/recommendations': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/next-match': 'http://localhost:8000',
      '/next-fixture': 'http://localhost:8000',
      '/fixtures': 'http://localhost:8000',
      '/opponents': 'http://localhost:8000',
    },
  },
  plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
