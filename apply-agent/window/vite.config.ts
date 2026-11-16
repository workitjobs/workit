import tailwind from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

// One self-contained HTML file: pywebview hands it to the window as a string,
// so the window opens no port and reads no file:// URL (design doc D11). It is
// built into the Python package (apply/student_page/index.html), so a Student
// build ships it with no Node; CI checks the committed file matches its source.
export default defineConfig({
  plugins: [react(), tailwind(), viteSingleFile()],
  build: { outDir: "../src/apply/student_page", emptyOutDir: true, assetsInlineLimit: Infinity },
});
