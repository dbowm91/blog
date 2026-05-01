import { defineConfig } from 'vite';
import { resolve } from 'path';
import { beasties } from 'vite-plugin-beasties';

export default defineConfig({
  root: resolve(__dirname, 'app/static'),
  build: {
    outDir: 'dist',
    assetsDir: '',
    manifest: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'app/static/js/main.js'),
      },
    },
  },
  plugins: [beasties()],
  server: {
    port: 3000,
    proxy: {
      '/': 'http://localhost:5000',
    },
  },
});
