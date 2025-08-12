import react from '@vitejs/plugin-react';
import fs from 'node:fs';
import path from 'node:path';
import { defineConfig, loadEnv } from 'vite';

// Read version from package.json for injection
const pkg = JSON.parse(fs.readFileSync(new URL('./package.json', import.meta.url), 'utf-8'));

export default defineConfig(({ mode }) => {
  // Load .env files and restrict variables with prefix VV_
  const env = loadEnv(mode, process.cwd(), 'VV_');
  return {
    plugins: [react()],
    publicDir: 'public',
    server: {
      port: 5173,
      strictPort: false,
      open: false,
      cors: true,
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
    preview: {
      port: 4173,
      strictPort: true,
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
      },
    },
    define: {
      __APP_VERSION__: JSON.stringify(pkg.version),
      __BUILD_MODE__: JSON.stringify(mode),
    },
    envPrefix: 'VV_',
    build: {
      outDir: 'dist',
      target: 'es2022',
      sourcemap: mode !== 'production',
      reportCompressedSize: true,
      chunkSizeWarningLimit: 600,
    },
    optimizeDeps: {
      include: ['react', 'react-dom'],
    },
    css: {
      modules: {
        localsConvention: 'camelCaseOnly',
      },
    },
  };
});
