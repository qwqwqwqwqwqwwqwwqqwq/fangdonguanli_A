import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Contract } from '@/types'
import api from '@/api'

export const useContractStore = defineStore('contract', () => {
  const list = ref<Contract[]>([])
  const current = ref<Contract | null>(null)
  const loading = ref(false)
  const listStale = ref(false)
  const currentFilter = ref<string | undefined>(undefined)

  async function fetchList(status?: string) {
    loading.value = true
    try {
      const { data } = await api.get('/contracts', { params: status ? { status } : {} })
      list.value = data
      listStale.value = false
      currentFilter.value = status
    } finally {
      loading.value = false
    }
  }

  function ensureFresh(status?: string) {
    if (listStale.value || list.value.length === 0 || currentFilter.value !== status) {
      return fetchList(status)
    }
  }

  async function fetchOne(id: number) {
    current.value = null
    const { data } = await api.get(`/contracts/${id}`)
    current.value = data
    return data as Contract
  }

  async function save(form: Record<string, unknown>) {
    if (form.id) {
      const { data } = await api.put(`/contracts/${form.id}`, form)
      return data
    } else {
      const { data } = await api.post('/contracts', form)
      return data
    }
  }

  async function cancel(id: number) {
    await api.post(`/contracts/${id}/cancel`)
  }

  async function startTermination(id: number) {
    const { data } = await api.post(`/contracts/${id}/start-termination`)
    return data.message as string
  }

  async function cancelTermination(id: number) {
    const { data } = await api.post(`/contracts/${id}/cancel-termination`)
    return data.message as string
  }

  async function uploadImage(id: number, file: File) {
    const fd = new FormData()
    fd.append('file', file)
    const { data } = await api.post(`/contracts/${id}/images`, fd)
    return data as Contract
  }

  async function deleteImage(contractId: number, imageId: number) {
    const { data } = await api.delete(`/contracts/${contractId}/images/${imageId}`)
    return data as Contract
  }

  return { list, current, loading, listStale, fetchList, fetchOne, save, cancel, startTermination, cancelTermination, uploadImage, deleteImage, ensureFresh }
})
