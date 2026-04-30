import { defineConfig } from 'vite';

export default defineConfig({
  root: 'app/static',
  build: {
    outDir: 'app/static/dist',
    assetsDir: '',
    rollupOptions: {
      input: {
        main: 'app/static/js/main.js',
      },
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/': 'http://localhost:5000',
    },
  },
});
