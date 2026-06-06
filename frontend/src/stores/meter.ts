import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { MeterReading } from '@/types'
import api from '@/api'

export const useMeterStore = defineStore('meter', () => {
  const list = ref<MeterReading[]>([])
  const loading = ref(false)
  const listStale = ref(false)

  async function fetchList(contractId: number) {
    loading.value = true
    try {
      const { data } = await api.get(`/meter-readings/contracts/${contractId}/readings`)
      list.value = data
      listStale.value = false
    } finally { loading.value = false }
  }

  async function fetchOne(id: number) {
    const { data } = await api.get(`/meter-readings/readings/${id}`)
    return data as MeterReading
  }

  async function create(payload: {
    contract_id: number; current_reading: number;
    reading_date: string; remark?: string
  }) {
    const { data } = await api.post('/meter-readings/readings', payload)
    listStale.value = true
    return data as MeterReading
  }

  async function update(id: number, payload: {
    current_reading?: number; electricity_amount?: number;
    reading_date?: string; remark?: string
  }) {
    const { data } = await api.put(`/meter-readings/readings/${id}`, payload)
    listStale.value = true
    return data
  }

  async function uploadPhoto(readingId: number, file: File) {
    const fd = new FormData()
    fd.append('file', file)
    const { data } = await api.post(`/meter-readings/readings/${readingId}/photo`, fd)
    return data
  }

  return { list, loading, listStale, fetchList, fetchOne, create, update, uploadPhoto }
})
