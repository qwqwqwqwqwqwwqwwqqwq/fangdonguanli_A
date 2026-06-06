<template>
  <div class="page">
    <van-nav-bar title="交房验收" left-arrow placeholder @click-left="$router.back()" />
    <div v-if="loading" class="loading"><van-loading /></div>
    <div v-else-if="insp" style="padding-bottom:60px;">
      <van-cell-group inset title="验收信息">
        <van-cell title="验收日期" :value="insp.inspection_date" />
        <van-cell title="电表底数" :value="String(insp.meter_base_reading)" />
        <van-cell title="钥匙交付" :value="insp.key_delivery_detail" />
      </van-cell-group>
      <van-cell-group inset title="物品清单" class="mt-16" v-if="insp.items?.length">
        <van-cell v-for="item in insp.items" :key="item.id" :title="item.item_name" :value="item.quantity + '件'">
          <template #label>
            <span :class="'tag-' + item.status">{{ item.status }}</span>
            <span v-if="item.defect_remark"> · {{ item.defect_remark }}</span>
          </template>
        </van-cell>
      </van-cell-group>
      <div style="margin:16px;" v-if="!insp.id">
        <van-button block type="primary" round @click="showForm = true">开始验收</van-button>
      </div>
    </div>
    <div v-else style="padding:16px;">
      <van-empty description="暂无交房验收记录" />
      <van-button block type="primary" round @click="showForm = true">开始验收</van-button>
    </div>

    <van-popup v-model:show="showForm" position="bottom" :style="{ height: '70%' }" round>
      <div style="padding:16px;">
        <h3>交房验收</h3>
        <van-field v-model="form.inspection_date" label="验收日期" type="date" placeholder="选择日期" :rules="[{ required: true, message: '请选择验收日期' }]" />
        <van-field v-model="form.meter_base_reading" label="电表底数" type="number" placeholder="0" />
        <van-field v-model="form.key_delivery_detail" label="钥匙交付" placeholder="如：钥匙2把" />
        <van-button block type="primary" round :loading="submitting" @click="submit" style="margin-top:16px;">确认验收</van-button>
      </div>
    </van-popup>
  </div>
</template>

<script setup lang="ts">
import { ref, inject } from 'vue'
import { useRoute, onBeforeRouteLeave } from 'vue-router'
import { showToast } from 'vant'
import api from '@/api'
import { useRefresh } from '@/composables/useRefresh'
import { useContractStore } from '@/stores/contract'
import type { MoveInInspection } from '@/types'

const route = useRoute()
const contractId = Number(route.params.id)
const insp = ref<MoveInInspection | null>(null)
const loading = ref(true)
const submitting = ref(false)
const showForm = ref(false)

const form = ref({ inspection_date: new Date().toISOString().slice(0, 10), meter_base_reading: '0', key_delivery_detail: '' })

async function fetch() {
  loading.value = true
  try {
    const { data } = await api.get(`/inspections/move-in/${contractId}`)
    insp.value = data
    showForm.value = false
  } catch {
    insp.value = null
    showToast('暂无交房验收记录，请先创建')
  } finally {
    loading.value = false
  }
}

async function submit() {
  submitting.value = true
  try {
    const { data } = await api.post('/inspections/move-in', {
      contract_id: contractId,
      inspection_date: form.value.inspection_date,
      meter_base_reading: Number(form.value.meter_base_reading),
      key_delivery_detail: form.value.key_delivery_detail,
    })
    insp.value = data
    showForm.value = false
    showToast('验收完成')
  } catch (e: any) {
    showToast(e.message || '验收失败')
  } finally {
    submitting.value = false
  }
}

const contractStore = useContractStore()
onBeforeRouteLeave(() => {
  contractStore.listStale = true
})

useRefresh(fetch)
</script>
