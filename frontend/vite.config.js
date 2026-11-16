import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // 개발 서버에서도 nginx 와 같은 경로(/api)로 백엔드를 부른다
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
