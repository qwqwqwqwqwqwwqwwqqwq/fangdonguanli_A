import axios, { AxiosError } from 'axios'

// 生产环境用完整后端地址，开发环境用 Vite 代理
const API_BASE = import.meta.env.VITE_API_BASE || '/api'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
})

api.interceptors.request.use((config) => {
  config.headers['X-API-Key'] = 'dev-key-change-me'
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
