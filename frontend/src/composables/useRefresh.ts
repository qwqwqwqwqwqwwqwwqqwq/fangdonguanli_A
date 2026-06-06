import { onMounted, onActivated } from 'vue'

/**
 * 确保组件每次进入时都重新加载数据。
 * - onMounted: 组件首次挂载
 * - onActivated: keep-alive 缓存组件激活时（当前未使用 keep-alive，但预留兼容）
 */
export function useRefresh(fn: () => void | Promise<void>) {
  onMounted(fn)
  onActivated(fn)
}
