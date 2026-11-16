import tailwind from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

// One self-contained HTML file: pywebview hands it to the window as a string,
// so the window opens no port and reads no file:// URL (design doc D11).
export default defineConfig({
  plugins: [react(), tailwind(), viteSingleFile()],
  build: { outDir: "dist", assetsInlineLimit: Infinity },
});
