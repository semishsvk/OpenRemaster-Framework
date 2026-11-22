// @ts-ignore The desktop config executes in Node. The pinned frontend dependencies omit Node types.
import { execFileSync } from "node:child_process";
import { defineConfig } from "vite";
import desktop from "./src-tauri/tauri.conf.json";

function sourceCommit(): string | null {
  const git = (args: string[]) => String(execFileSync("git", args, {
    cwd: new URL(".", import.meta.url), encoding: "utf8", stdio: ["ignore", "pipe", "ignore"],
  })).trim();
  try {
    git(["ls-files", "--error-unmatch", "vite.config.ts"]);
    if (git(["status", "--porcelain", "--", "."])) return null;
    const commit = git(["rev-parse", "HEAD"]);
    return /^[a-f0-9]{40}$/.test(commit) ? commit : null;
  } catch {
    return null;
  }
}

export default defineConfig(({command}) => ({
  base: "./",
  define: {
    __STUDIO_BUILD__: JSON.stringify({
      version: desktop.version,
      commit: command === "build" ? sourceCommit() : null,
      builtAt: command === "build" ? new Date().toISOString() : null,
    }),
  },
  server: {host: "127.0.0.1", port: 1420, strictPort: true},
  build: {outDir: "dist", sourcemap: false, emptyOutDir: true, rollupOptions: {output: {manualChunks: {"react-vendor": ["react", "react-dom", "react-dom/client"]}}}},
}));
