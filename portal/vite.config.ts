import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 8081,
    strictPort: true,
    allowedHosts: ['localhost', '127.0.0.1', 'maestro-portal'],
    proxy: {
      '/api': {
        target: 'http://maestro-api:8080',
        changeOrigin: true,
      },
      '/oauth': {
        target: 'http://maestro-api:8080',
        changeOrigin: true,
      },
    },
    watch: {
      usePolling: true, // WSL2 / Docker volumes
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
