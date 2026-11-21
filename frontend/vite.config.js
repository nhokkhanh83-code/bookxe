import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Strip crossorigin attribute for non-CORS-enabled servers
function stripCrossorigin() {
  return {
    name: "strip-crossorigin",
    transformIndexHtml(html) {
      return html.replace(/ crossorigin/g, "");
    },
  };
}

export default defineConfig({
  plugins: [react(), stripCrossorigin()],
  server: {
    port: 5173,
    host: true,
  },
  build: {
    outDir: "dist",
  },
});
