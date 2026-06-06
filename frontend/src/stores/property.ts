import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Property } from '@/types'
import api from '@/api'

export const usePropertyStore = defineStore('property', () => {
  const list = ref<Property[]>([])
  const current = ref<Property | null>(null)
  const loading = ref(false)
  const listStale = ref(false)

  async function fetchList(status?: string) {
    loading.value = true
    try {
      const { data } = await api.get('/properties', { params: status ? { status } : {} })
      list.value = data
      listStale.value = false
    } finally {
      loading.value = false
    }
  }

  async function fetchOne(id: number) {
    const { data } = await api.get(`/properties/${id}`)
    current.value = data
    return data
  }

  async function save(form: Partial<Property>) {
    if (form.id) {
      const { data } = await api.put(`/properties/${form.id}`, form)
      return data
    } else {
      const { data } = await api.post('/properties', form)
      return data
    }
  }

  async function remove(id: number) {
    await api.delete(`/properties/${id}`)
    list.value = list.value.filter((p) => p.id !== id)
  }

  return { list, current, loading, listStale, fetchList, fetchOne, save, remove }
})
