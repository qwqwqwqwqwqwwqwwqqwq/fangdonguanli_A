import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Settlement } from '@/types'
import api from '@/api'

export const useSettlementStore = defineStore('settlement', () => {
  const current = ref<Settlement | null>(null)
  const loading = ref(false)

  async function fetchOne(contractId: number) {
    loading.value = true
    try {
      const { data } = await api.get(`/settlements/${contractId}`)
      current.value = data
      return data as Settlement
    } finally { loading.value = false }
  }

  async function create(contractId: number, payload?: { other_deduction?: number; remark?: string }) {
    const { data } = await api.post(`/settlements/${contractId}`, payload || {})
    current.value = data
    return data as Settlement
  }

  async function confirm(contractId: number, payload: {
    refund_date: string; refund_method: string; remark?: string
  }) {
    const { data } = await api.post(`/settlements/${contractId}/confirm`, payload)
    current.value = data
    return data as Settlement
  }

  return { current, loading, fetchOne, create, confirm }
})
