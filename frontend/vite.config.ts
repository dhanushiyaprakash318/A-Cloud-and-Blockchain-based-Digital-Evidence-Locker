import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import proxyConfig from './vite.proxy.config';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 5173,
    proxy: proxyConfig,
  },
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
