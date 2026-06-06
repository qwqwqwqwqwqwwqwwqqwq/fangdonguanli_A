import axios, { AxiosError } from 'axios'

// 后端地址：生产构建时由 .env.production 的 VITE_API_BASE 决定
// 开发时未设置则使用 Vite 代理（/api → localhost:8005）
const API_BASE = import.meta.env.VITE_API_BASE || '/api'

// API Key：生产构建时必须通过 VITE_API_KEY 环境变量设置
// 默认值仅用于本地开发（与 backend 默认值一致）
const API_KEY = import.meta.env.VITE_API_KEY || 'dev-key-change-me'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
})

api.interceptors.request.use((config) => {
  config.headers['X-API-Key'] = API_KEY
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err: AxiosError<{ detail?: string }>) => {
    const msg = err.response?.data?.detail || err.message || '请求失败'
    const error = new Error(msg) as Error & { status?: number }
    error.status = err.response?.status
    return Promise.reject(error)
  },
)

export default api
