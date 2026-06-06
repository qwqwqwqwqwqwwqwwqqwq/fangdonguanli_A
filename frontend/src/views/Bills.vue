<template>
  <div class="page">
    <van-nav-bar title="账单管理" left-arrow placeholder @click-left="$router.back()" />
    <van-tabs v-model:active="statusTab" @change="fetchList">
      <van-tab title="全部" name="" />
      <van-tab title="未付" name="未付" />
      <van-tab title="逾期" name="逾期" />
      <van-tab title="部分付" name="部分付" />
      <van-tab title="已付" name="已付" />
    </van-tabs>
    <van-cell-group inset v-if="bills.length">
      <van-cell v-for="b in bills" :key="b.id" :title="b.bill_month + ' ' + b.property_name" :label="'房租¥' + b.rent + ' · 水电¥' + b.water_fee + '+' + b.electricity_fee + ' · 到期' + b.due_date" :value="'合计 ¥' + b.total" is-link @click="$router.push(`/bills/${b.id}`)">
        <template #extra>
          <span :class="'tag-' + displayStatus(b)" style="font-size:12px;">{{ displayStatus(b) }}</span>
        </template>
      </van-cell>
    </van-cell-group>
    <van-empty v-else description="暂无账单" image="search" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'
import { useRefresh } from '@/composables/useRefresh'
import { displayBillStatus as displayStatus } from '@/composables/useBillStatus'
import type { Bill } from '@/types'

const route = useRoute()
const contractId = computed(() => Number(route.query.contract_id || 0))
const contractIdsParam = computed(() => (route.query.contract_ids as string) || '')
const bills = ref<Bill[]>([])
const statusTab = ref((route.query.status as string) || '')
const autoGenerating = ref(false)
const billsLoading = ref(true)

async function fetchList() {
  const params: Record<string, string> = {}
  if (statusTab.value) params.status = statusTab.value
  if (contractId.value) params.contract_id = String(contractId.value)
  if (contractIdsParam.value) params.contract_ids = contractIdsParam.value

  // 自动补全缺失月份的账单
  if (!autoGenerating.value) {
    autoGenerating.value = true
    try {
      const genParams: Record<string, any> = {}
      if (contractId.value) genParams.contract_id = contractId.value
      await api.post('/bills/auto-generate', null, { params: genParams })
    } catch {
      // 静默失败，不影响列表查看
    } finally {
      autoGenerating.value = false
    }
  }

  const { data } = await api.get('/bills', { params })
  bills.value = data
  billsLoading.value = false
}

useRefresh(fetchList)
</script>
