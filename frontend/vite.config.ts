import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // `npm run preview` of a production build calls same-origin /api (as on Vercel).
  preview: { proxy: { '/api': 'http://localhost:8000' } },
})
