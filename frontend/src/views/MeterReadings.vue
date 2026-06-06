<template>
  <div class="page">
    <van-nav-bar title="电表记录" left-arrow placeholder @click-left="$router.back()" />
    <div v-if="readingsLoading" class="skeleton-row" style="padding:0 16px;">
      <van-skeleton title :row="3" v-for="i in 2" :key="i" />
    </div>
    <van-cell-group inset v-if="readings.length">
      <van-cell v-for="r in readings" :key="r.id" :title="r.reading_date || '—'" :label="'用电' + (r.consumption != null ? r.consumption : '—') + '度 · ¥' + r.electricity_amount" :value="'读数：' + (r.last_reading ?? '?') + ' → ' + r.current_reading" is-link @click="$router.push(`/meter-readings/${r.id}/edit`)" />
    </van-cell-group>
    <div v-if="!readingsLoading && readings.length > 0" style="padding:8px 16px;font-size:12px;color:#999;">
      共 {{ readings.length }} 次抄表 · 累计用电 {{ readings.reduce((s,r) => s + (r.consumption || 0), 0) }} kWh · 电费 {{ readings.reduce((s,r) => s + r.electricity_amount, 0) }} 元
    </div>
    <van-empty v-else-if="!readingsLoading" description="暂无电表记录" image="search">
        <template #default>
          <p class="text-secondary" style="font-size:12px;">点击下方按钮创建第一笔抄表</p>
        </template>
      </van-empty>
    <div style="margin:16px;">
      <van-button v-if="contractStatus === '已租' || contractStatus === '退租处理中'" block type="primary" round @click="showForm = true">新增抄表</van-button>
    </div>

    <van-popup v-model:show="showForm" position="bottom" :style="{ height: '55%' }" round>
      <div style="padding:16px;">
        <h3>新增抄表</h3>
        <van-field v-model="form.current_reading" label="当前读数" type="number" placeholder="0" :rules="[{ required: true, message: '请输入当前读数' }]" />
        <van-field v-model="form.reading_date" label="抄表日期" type="date" placeholder="选择日期" :rules="[{ required: true, message: '请输入抄表日期' }]" />
        <van-field v-model="form.remark" label="备注" placeholder="选填" />
        <p style="color:#999;font-size:12px;padding:8px 16px 0;">电费金额将自动计算（当前读数 - 上次读数）</p>
        <van-button block type="primary" round :loading="submitting" @click="submit" style="margin-top:12px;">保存</van-button>
      </div>
    </van-popup>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { showToast } from 'vant'
import api from '@/api'
import { useRefresh } from '@/composables/useRefresh'
import type { MeterReading } from '@/types'

const route = useRoute()
const contractId = Number(route.query.contract_id || 0)
const readings = ref<MeterReading[]>([])
const showForm = ref(false)
const readingsLoading = ref(true)
const submitting = ref(false)
const contractStatus = ref('')
const form = ref({ current_reading: '0', reading_date: new Date().toISOString().slice(0, 10), remark: '' })

async function fetch() {
  // Load contract status to conditionally hide add button
  try {
    const { data: ct } = await api.get(`/contracts/${contractId}`)
    contractStatus.value = ct.status
  } catch {}
  const { data } = await api.get(`/meter-readings/contracts/${contractId}/readings`)
  readings.value = data
  readingsLoading.value = false
}

async function submit() {
  submitting.value = true
  try {
    await api.post('/meter-readings/readings', {
      contract_id: contractId,
      current_reading: Number(form.value.current_reading),
      reading_date: form.value.reading_date,
      remark: form.value.remark,
    })
    showForm.value = false
    showToast('保存成功')
    await fetch()
  } catch (e: any) {
    showToast(e.message || '保存失败')
  } finally {
    submitting.value = false
  }
}

useRefresh(fetch)
</script>
