<template>
  <div class="page">
    <van-nav-bar title="编辑抄表" left-arrow placeholder @click-left="$router.back()" />
    <van-form @submit="submit" style="padding:16px;">
      <van-field v-model="form.current_reading" label="当前读数" type="number" :rules="[{ required: true, message: '请输入当前读数' }]" />
      <van-field v-model="form.electricity_amount" label="电费金额" type="number" />
      <van-field v-model="form.reading_date" label="抄表日期" type="date" placeholder="选择日期" />
      <van-field v-model="form.remark" label="备注" />
      <div style="margin:16px 0;">
        <van-button block type="primary" round native-type="submit" :loading="submitting">保存</van-button>
      </div>
    </van-form>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import api from '@/api'

const route = useRoute()
const router = useRouter()
const id = Number(route.params.id)
const submitting = ref(false)
const contractId = ref(0)
const form = reactive({ current_reading: '', electricity_amount: '', reading_date: new Date().toISOString().slice(0, 10), remark: '' })

onMounted(async () => {
  try {
    const { data } = await api.get(`/meter-readings/readings/${id}`)
    if (data) {
      Object.assign(form, data)
      contractId.value = data.contract_id || 0
    }
  } catch (e: any) {
    showToast(e.message || '加载抄表记录失败')
  }
})

async function submit() {
  submitting.value = true
  try {
    await api.put(`/meter-readings/readings/${id}`, {
      current_reading: Number(form.current_reading),
      electricity_amount: Number(form.electricity_amount),
      reading_date: form.reading_date,
      remark: form.remark,
    } as Record<string, unknown>)
    showToast('保存成功')
    router.replace(`/meter-readings?contract_id=${contractId.value}`)
  } catch (e: any) {
    showToast(e.message || '保存失败')
  } finally {
    submitting.value = false
  }
}
</script>
