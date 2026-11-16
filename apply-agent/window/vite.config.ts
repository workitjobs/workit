import { join } from "node:path";

import tailwind from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

// One self-contained HTML file: pywebview hands it to the window as a string,
// so the window opens no port and reads no file:// URL (design doc D11). It is
// built into the Python package (apply/student_page/index.html), so a Student
// build ships it with no Node; CI checks the committed file matches its source.
//
// Logos load from Brandfetch with WorkIt's public client id, the website's own NEXT_PUBLIC_BRANDFETCH_CLIENT_ID: from
// the environment (CI's apply-window job sets it from the repo's variables, as deploy.yml does for the website), else
// from frontend/.env.local. With none, the page skips Brandfetch, as the website's jobLogo does. The committed page is
// built with it, so a build without it differs from the committed file.
export default defineConfig(({ mode }) => ({
  plugins: [react(), tailwind(), viteSingleFile()],
  define: {
    __BRANDFETCH_CLIENT_ID__: JSON.stringify(
      loadEnv(mode, join(import.meta.dirname, "..", "..", "frontend"), "NEXT_PUBLIC_").NEXT_PUBLIC_BRANDFETCH_CLIENT_ID ?? "",
    ),
  },
  build: { outDir: join(import.meta.dirname, "..", "src", "apply", "student_page"), emptyOutDir: true, assetsInlineLimit: Infinity },
}));
