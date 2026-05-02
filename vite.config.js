import { defineConfig } from 'vite';
import { resolve } from 'path';

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
  plugins: [],
  server: {
    port: 3000,
    proxy: {
      '/': 'http://localhost:5000',
    },
  },
  optimizeDeps: {
    esbuildOptions: {
      loader: {
        '.js': 'js',
        '.jsx': 'jsx',
        '.svg': 'text',
      },
      target: ['chrome100', 'edge100', 'firefox100', 'safari15'],
      include: [],
    },
  },
});
