import react from "@vitejs/plugin-react-swc";
import path from "path";
import { defineConfig } from "vite";
import { visualizer } from "rollup-plugin-visualizer";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const API_BASE_URL = process.env.API_BASE_URL;
  const VITE_ALLOWED_HOSTS = process.env.VITE_ALLOWED_HOSTS
    ? process.env.VITE_ALLOWED_HOSTS.split(',').map(host => host.trim())
    : ['localhost', '127.0.0.1', '0.0.0.0'];

  return {
    server: {
      host: "0.0.0.0",
      port: 5000,
      strictPort: true,
      allowedHosts: VITE_ALLOWED_HOSTS,
      proxy: {
        '/api': {
          target: API_BASE_URL,
          changeOrigin: true,
          secure: false,
          ws: true,
          rewrite: (path) => path.replace(/^\/api/, '/api')
        }
      }
    },
    plugins: [
      react(),
      mode === "development",
      // Bundle analysis with gzip size tracking
      visualizer({
        filename: './dist/stats.html',
        open: false,
        gzipSize: true,
        brotliSize: false,
      })
    ].filter(Boolean),
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            // Separate vendor code into logical chunks for better caching
            'react-vendor': ['react', 'react-dom', 'react-router-dom'],
            'ui-vendor': [
              '@radix-ui/react-progress',
              '@radix-ui/react-slot',
              '@radix-ui/react-toast',
              '@radix-ui/react-tooltip',
              'lucide-react',
              'framer-motion',
              'next-themes',
              'sonner'
            ],
            'query-vendor': ['@tanstack/react-query'],
            'socket-vendor': ['socket.io-client'],
          },
        },
      },
      // Warn if chunk exceeds 500KB
      chunkSizeWarningLimit: 500,
      // Enable tree shaking for unused code elimination
      minify: 'esbuild',
    },
    test: {
      globals: true,
      environment: "jsdom",
      setupFiles: "./src/test/setup.ts",
      css: true,
    },
  };
});
