import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { MoveInInspection, MoveOutInspection } from '@/types'
import api from '@/api'

export const useInspectionStore = defineStore('inspection', () => {
  const moveIn = ref<MoveInInspection | null>(null)
  const moveOut = ref<MoveOutInspection | null>(null)
  const loading = ref(false)

  // --- 交房验收 ---
  async function fetchMoveIn(contractId: number) {
    loading.value = true
    try {
      const { data } = await api.get(`/inspections/move-in/${contractId}`)
      moveIn.value = data
      return data as MoveInInspection
    } finally { loading.value = false }
  }

  async function createMoveIn(payload: {
    contract_id: number; inspection_date: string;
    meter_base_reading: number; key_delivery_detail?: string
  }) {
    const { data } = await api.post('/inspections/move-in', payload)
    moveIn.value = data
    return data as MoveInInspection
  }

  async function updateMoveInItem(inspectionId: number, itemId: number, payload: {
    status: string; defect_remark?: string
  }) {
    const { data } = await api.put(`/inspections/move-in/${inspectionId}/items/${itemId}`, payload)
    return data
  }

  async function uploadMoveInImage(inspectionId: number, file: File) {
    const fd = new FormData()
    fd.append('file', file)
    const { data } = await api.post(`/inspections/move-in/${inspectionId}/images`, fd)
    return data
  }

  async function uploadSignature(inspectionId: number, role: 'landlord' | 'tenant', file: File) {
    const fd = new FormData()
    fd.append('file', file)
    const { data } = await api.post(`/inspections/move-in/${inspectionId}/signatures?role=${role}`, fd)
    return data
  }

  // --- 退房验收 ---
  async function fetchMoveOut(contractId: number) {
    loading.value = true
    try {
      const { data } = await api.get(`/inspections/move-out/${contractId}`)
      moveOut.value = data
      return data as MoveOutInspection
    } finally { loading.value = false }
  }

  async function createMoveOut(payload: {
    contract_id: number; inspection_date: string;
    meter_reading: number; key_return_status?: string;
    key_deduction?: number; electricity_deduction?: number; remark?: string
  }) {
    const { data } = await api.post('/inspections/move-out', payload)
    moveOut.value = data
    return data as MoveOutInspection
  }

  async function updateMoveOutItem(inspectionId: number, itemId: number, payload: {
    status: string; deduction_amount: number
  }) {
    const { data } = await api.put(`/inspections/move-out/${inspectionId}/items/${itemId}`, payload)
    return data
  }

  async function updateMoveOut(inspectionId: number, payload: Record<string, unknown>) {
    const { data } = await api.put(`/inspections/move-out/${inspectionId}`, payload)
    moveOut.value = data
    return data
  }

  async function uploadMoveOutImage(inspectionId: number, file: File) {
    const fd = new FormData()
    fd.append('file', file)
    const { data } = await api.post(`/inspections/move-out/${inspectionId}/images`, fd)
    return data
  }

  return {
    moveIn, moveOut, loading,
    fetchMoveIn, createMoveIn, updateMoveInItem, uploadMoveInImage, uploadSignature,
    fetchMoveOut, createMoveOut, updateMoveOutItem, updateMoveOut, uploadMoveOutImage,
  }
})
