import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';

// Local development only. A deployed site needs its own /api reverse proxy.
const proxy = { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } };

export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        workspace: fileURLToPath(new URL('./workspace.html', import.meta.url)),
        main: fileURLToPath(new URL('./index.html', import.meta.url)),
        research: fileURLToPath(new URL('./research.html', import.meta.url)),
      }
    }
  },
  server: { host: '127.0.0.1', port: 5173, strictPort: true, proxy },
  preview: { host: '127.0.0.1', port: 4173, strictPort: true, proxy },
});
