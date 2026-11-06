import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

const projectFile = (relativePath) => fileURLToPath(new URL(relativePath, import.meta.url));

export default defineConfig({
  base: "/forgepilot/",
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        app: projectFile("./index.html"),
        showcase: projectFile("./showcase/index.html"),
      },
    },
  },
  server: {
    port: 5173,
  },
});
