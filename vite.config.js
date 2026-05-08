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
      output: {
        manualChunks: {
          'vendor': ['prism.min.js', 'prism-languages.js'],
          'admin': resolve(__dirname, 'app/static/js/admin/editor.js'),
          'public': resolve(__dirname, 'app/static/js/public/search.js'),
        },
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
