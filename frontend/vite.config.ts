import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const API_TARGET = process.env.COSPAL_API ?? 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 1100,
  },
  server: {
    proxy: {
      '/api': API_TARGET,
      '/media': API_TARGET,
    },
  },
});
