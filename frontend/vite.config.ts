import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// Proxy API calls to the backend, but let browser navigations (Accept: text/html)
// fall through to the SPA instead of returning raw JSON.
const apiProxy = (target = "http://localhost:8000") => ({
  target,
  bypass(req: { headers: { accept?: string } }) {
    if (req.headers.accept?.includes("text/html")) return req.url;
  },
});

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
    hmr: {
      overlay: false,
    },
    proxy: {
      '/chat': apiProxy(),
      '/chat/stream': apiProxy(),
      '/predict': apiProxy(),
      '/predict/analysis': apiProxy(),
      '/commentary': apiProxy(),
      '/articles': apiProxy(),
      '/recommendations': apiProxy(),
      '/health': apiProxy(),
      '/next-match': apiProxy(),
      '/next-fixture': apiProxy(),
      '/season': apiProxy(),
      '/results': apiProxy(),
      '/standings': apiProxy(),
      '/form': apiProxy(),
      '/history': apiProxy(),
      '/h2h': apiProxy(),
      '/calls': apiProxy(),
      '/conversations': apiProxy(),
      '/fixtures': apiProxy(),
      '/opponents': apiProxy(),
    },
  },
  plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
