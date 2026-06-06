<template>
  <div class="page">
    <van-nav-bar title="账单详情" left-arrow placeholder @click-left="$router.back()" />
    <div v-if="!b" class="loading" style="padding:60px;"><van-loading /></div>
    <div v-else style="padding-bottom:60px;">
      <!-- 账单概要 -->
      <div class="card">
        <div class="flex-between">
          <span style="font-size:16px;font-weight:600;">{{ b.bill_code }}</span>
          <span :class="'tag-' + displayBillStatus(b)" style="font-size:15px;">{{ displayBillStatus(b) }}</span>
        </div>
        <div class="text-secondary" style="margin-top:4px;">房产：{{ b.property_name }} · 租客：{{ b.tenant_name }}</div>
      </div>

      <!-- 收款进度条 -->
      <div class="card" v-if="paidTotal > 0 || b.status !== '已付'">
        <div class="flex-between" style="margin-bottom:6px;">
          <span style="font-size:13px;">已付 <b style="color:var(--success);">¥{{ paidTotal }}</b></span>
          <span style="font-size:13px;" :style="{ color: remaining > 0 ? 'var(--danger)' : 'var(--success)' }">待付 <b>¥{{ remaining }}</b></span>
        </div>
        <van-progress :percentage="paidPercent" :stroke-color="paidPercent >= 100 ? 'var(--success)' : 'var(--primary)'" stroke-width="6" />
        <div class="text-secondary" style="margin-top:4px;font-size:12px;">账单总额 ¥{{ b.total }}</div>
      </div>

      <!-- 费用明细 -->
      <van-cell-group inset title="费用明细">
        <van-cell title="房租" :value="'¥' + b.rent" />
        <van-cell title="水费" :value="'¥' + b.water_fee" />
        <van-cell title="电费" :value="'¥' + b.electricity_fee" />
        <van-cell title="其他费用" :value="'¥' + b.other_fee" />
        <van-cell v-for="f in b.other_fees" :key="f.id" :title="'  └ ' + f.fee_name" :value="'¥' + f.amount" />
        <van-cell title="合计" :value="'¥' + b.total" style="font-weight:600;" />
      </van-cell-group>

      <!-- 收款记录 -->
      <van-cell-group inset title="收款记录" class="mt-16" v-if="payments.length">
        <van-cell v-for="p in payments" :key="p.id">
          <template #title>
            <span style="font-weight:500;">¥{{ p.amount }}</span>
            <span class="text-secondary" style="margin-left:6px;font-size:12px;">{{ p.payment_method }}</span>
          </template>
          <template #label>
            <span>日期：{{ p.payment_date }}</span>
            <span v-if="p.remark" class="text-secondary" style="margin-left:4px;">· {{ p.remark }}</span>
          </template>
        </van-cell>
      </van-cell-group>
      <div v-else class="text-secondary" style="text-align:center;padding:12px;font-size:13px;">
        {{ b.status === '已付' ? '暂未记录收款明细' : '暂无收款记录，点击下方按钮收款' }}
      </div>

      <!-- 账单信息 -->
      <van-cell-group inset title="账单信息" class="mt-16">
        <van-cell title="账单月份" :value="b.bill_month" />
        <van-cell title="生成日期" :value="b.generated_date" />
        <van-cell title="到期日" :value="b.due_date" />
      </van-cell-group>

      <!-- 操作按钮 -->
      <div style="margin:16px;">
        <van-button v-if="b.status !== '已付'" block type="primary" round @click="$router.push(`/payments/new?bill_id=${b.id}&amount=${remaining}`)">收款</van-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'
import { useRefresh } from '@/composables/useRefresh'
import { displayBillStatus } from '@/composables/useBillStatus'
import type { Bill, BillPaymentRecord } from '@/types'

const route = useRoute()
const b = ref<Bill | null>(null)
const payments = ref<BillPaymentRecord[]>([])

const paidTotal = computed(() => Math.round(payments.value.reduce((s, p) => s + p.amount, 0) * 1e10) / 1e10)
const remaining = computed(() => {
  if (!b.value) return 0
  return Math.round(Math.max(0, b.value.total - paidTotal.value) * 1e10) / 1e10
})
const paidPercent = computed(() => {
  if (!b.value || b.value.total === 0) return 0
  const raw = (paidTotal.value / b.value.total) * 100
  return Math.min(100, Math.round(raw * 10) / 10)
})

useRefresh(async () => {
  const { data } = await api.get(`/bills/${route.params.id}`)
  b.value = data
  try {
    const { data: pdata } = await api.get(`/bills/${route.params.id}/payments`)
    payments.value = pdata || []
  } catch {
    payments.value = []
  }
})
</script>
