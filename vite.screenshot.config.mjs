// 临时配置：仅用于本地截图取证（不提交）
// 作用等同于 `edgeone makers dev` 注入的代理，把前端请求转发到 127.0.0.1:8088
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const target = 'http://127.0.0.1:8088';
const proxy = Object.fromEntries(
  ['/chat', '/chat/stop', '/stop', '/history', '/conversations', '/clear-history', '/delete-conversation', '/health'].map(
    (p) => [p, { target, changeOrigin: true }],
  ),
);

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy,
  },
});
