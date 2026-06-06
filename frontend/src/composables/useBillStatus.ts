import type { Bill } from '@/types'

export function displayBillStatus(b: Bill): string {
  if (b.status === '未付' || b.status === '部分付') {
    const now = new Date()
    const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
    if (b.due_date < today) return '逾期'
  }
  return b.status
}
