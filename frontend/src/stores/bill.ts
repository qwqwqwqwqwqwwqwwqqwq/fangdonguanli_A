import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Bill, BillStatus } from '@/types'
import api from '@/api'

export const useBillStore = defineStore('bill', () => {
  const list = ref<Bill[]>([])
  const current = ref<Bill | null>(null)
  const loading = ref(false)
  const listStale = ref(false)

  async function fetchList(params?: { contract_id?: number; status?: BillStatus | '逾期' }) {
    loading.value = true
    try {
      const { data } = await api.get('/bills', { params })
      list.value = data
      listStale.value = false
    } finally { loading.value = false }
  }

  async function fetchOne(id: number) {
    const { data } = await api.get(`/bills/${id}`)
    current.value = data
    return data as Bill
  }

  async function generate(contractId: number, billMonth: string) {
    const { data } = await api.post(`/bills/generate/${contractId}`, { bill_month: billMonth })
    return data as Bill
  }

  async function autoGenerate(contractId?: number) {
    const { data } = await api.post('/bills/auto-generate', contractId ? { contract_id: contractId } : {})
    return data
  }

  async function addOtherFee(billId: number, fee: { fee_name: string; amount: number; remark?: string }) {
    const { data } = await api.post(`/bills/${billId}/other-fees`, fee)
    listStale.value = true
    return data
  }

  async function sendDunning(billId: number, smsContent: string) {
    const { data } = await api.post(`/bills/${billId}/dunning`, { sms_content: smsContent })
    return data
  }

  async function getBillPayments(billId: number) {
    const { data } = await api.get(`/bills/${billId}/payments`)
    return data
  }

  return { list, current, loading, listStale, fetchList, fetchOne, generate, autoGenerate, addOtherFee, sendDunning, getBillPayments }
})
