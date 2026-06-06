import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { VantResolver } from '@vant/auto-import-resolver'
import { resolve } from 'path'

export default defineConfig({
  // base: './' 使用相对路径，兼容 GitHub Pages 子目录部署
  base: './',
  plugins: [
    vue(),
    Components({ resolvers: [VantResolver()] }),
  ],
  resolve: { alias: { '@': resolve(__dirname, 'src') } },
  server: { port: 5173, host: '0.0.0.0', proxy: { '/api': 'http://localhost:8005', '/uploads': 'http://localhost:8005', '/guide': 'http://localhost:8005' } },
})
