import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Tenant, TenantCredit } from '@/types'
import api from '@/api'

export const useTenantStore = defineStore('tenant', () => {
  const list = ref<Tenant[]>([])
  const loading = ref(false)
  const listStale = ref(false)

  async function fetchList() {
    loading.value = true
    try {
      const { data } = await api.get('/tenants')
      list.value = data
      listStale.value = false
    } finally {
      loading.value = false
    }
  }

  async function fetchOne(id_number: string) {
    const { data } = await api.get(`/tenants/${id_number}`)
    return data as Tenant
  }

  async function fetchCredit(id_number: string) {
    const { data } = await api.get(`/tenants/${id_number}/credit`)
    return data as TenantCredit
  }

  async function save(form: Partial<Tenant> & { id_number: string }) {
    const existing = list.value.find((t) => t.id_number === form.id_number)
    if (existing) {
      const { data } = await api.put(`/tenants/${form.id_number}`, form)
      return data
    } else {
      const { data } = await api.post('/tenants', form)
      return data
    }
  }

  async function remove(id_number: string) {
    await api.delete(`/tenants/${id_number}`)
    list.value = list.value.filter((t) => t.id_number !== id_number)
  }

  return { list, loading, listStale, fetchList, fetchOne, fetchCredit, save, remove }
})
