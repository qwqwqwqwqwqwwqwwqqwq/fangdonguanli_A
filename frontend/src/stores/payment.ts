import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Payment } from '@/types'
import api from '@/api'

export const usePaymentStore = defineStore('payment', () => {
  const list = ref<Payment[]>([])
  const loading = ref(false)
  const listStale = ref(false)

  async function fetchList() {
    loading.value = true
    try {
      const { data } = await api.get('/payments')
      list.value = data
      listStale.value = false
    } finally { loading.value = false }
  }

  async function fetchOne(id: number) {
    const { data } = await api.get(`/payments/${id}`)
    return data as Payment
  }

  async function createSingle(payload: {
    bill_id: number; amount: number; payment_date: string;
    payment_method: string; remark?: string
  }) {
    const { data } = await api.post('/payments/single', payload)
    listStale.value = true
    return data as Payment
  }

  async function createBatch(payload: {
    bill_ids: number[]; total_amount: number; payment_date: string;
    payment_method: string; remark?: string
  }) {
    const { data } = await api.post('/payments/batch', payload)
    listStale.value = true
    return data as Payment
  }

  return { list, loading, listStale, fetchList, fetchOne, createSingle, createBatch }
})
