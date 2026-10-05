import { defineConfig } from "vite";

// @vitejs/plugin-react is not needed for a production build: Oxc compiles JSX with React's automatic runtime.
export default defineConfig({
  oxc: { jsx: { runtime: "automatic" } },
  build: { outDir: "dist", sourcemap: false },
});
