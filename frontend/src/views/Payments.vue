<template>
  <div class="page">
    <van-nav-bar title="收款记录" left-arrow placeholder @click-left="$router.back()" />
    <div v-if="paymentsLoading" class="skeleton-row" style="padding:0 16px;">
      <van-skeleton title :row="2" v-for="i in 3" :key="i" />
    </div>
    <van-cell-group inset v-if="!paymentsLoading && payments.length">
      <van-cell v-for="p in payments" :key="p.id" :title="'收款金额 ¥' + p.total_amount" :label="'日期：' + p.payment_date + ' · 方式：' + p.payment_method">
        <template #value>
          <span class="text-secondary" style="font-size:11px;">账单：{{ p.allocations?.map(a => a.bill_code).join(', ') || '—' }}</span>
        </template>
      </van-cell>
    </van-cell-group>
    <van-empty v-else description="暂无收款记录" image="search" />
    <div style="margin:16px;">
      <van-button block type="primary" round @click="$router.push('/payments/new')">新增收款</van-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import api from '@/api'
import { useRefresh } from '@/composables/useRefresh'
import type { Payment } from '@/types'

const payments = ref<Payment[]>([])
const paymentsLoading = ref(true)

useRefresh(async () => {
  const { data } = await api.get('/payments')
  payments.value = data
  paymentsLoading.value = false
})
</script>
