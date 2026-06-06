<template>
  <div class="page">
    <van-nav-bar title="退租结算" left-arrow placeholder @click-left="$router.back()" />
    <div v-if="!s" class="loading" style="padding:60px;"><van-loading /></div>
    <div v-else style="padding-bottom:60px;">
      <van-cell-group inset title="结算明细">
        <van-cell title="押金总额" :value="'¥' + s.deposit_total" />
        <van-cell title="电费扣款" :value="'-¥' + s.electricity_deduction" />
        <van-cell title="物品损坏扣款" :value="'-¥' + s.item_damage_deduction" />
        <van-cell title="物品缺失扣款" :value="'-¥' + s.item_missing_deduction" />
        <van-cell title="钥匙扣款" :value="'-¥' + s.key_deduction" />
        <van-cell title="未付账单扣款" :value="'-¥' + s.unpaid_bills_total" />
        <van-cell title="其他扣款" :value="'-¥' + s.other_deduction" />
        <van-cell title="实际退款" :value="'¥' + s.actual_refund" style="font-weight:600;font-size:16px;color:var(--primary);" />
      </van-cell-group>
      <van-cell-group inset title="未付账单" class="mt-16" v-if="s.unpaid_bills_note">
        <van-cell :value="s.unpaid_bills_note" is-link @click="$router.push(`/bills?contract_id=${contractId}&status=未付`)" />
      </van-cell-group>
      <van-cell-group inset title="退款信息" class="mt-16" v-if="s.refund_date">
        <van-cell title="退款日期" :value="s.refund_date" />
        <van-cell title="退款方式" :value="s.refund_method || ''" />
      </van-cell-group>

      <div style="margin:16px;">
        <van-button v-if="!s.refund_date" block type="primary" round @click="showConfirm = true">确认退款</van-button>
      </div>
    </div>

    <van-popup v-model:show="showConfirm" position="bottom" :style="{ height: '50%' }" round>
      <div style="padding:16px;">
        <h3>确认退款</h3>
        <van-field v-model="form.refund_date" label="退款日期" type="date" placeholder="选择日期" :rules="[{ required: true, message: '请选择退款日期' }]" />
        <van-field v-model="form.refund_method" label="退款方式" placeholder="微信/支付宝/银行转账/现金" :rules="[{ required: true, message: '请选择退款方式' }]" />
        <van-field v-model="form.remark" label="备注" />
        <van-button block type="primary" round :loading="submitting" @click="confirm" style="margin-top:16px;">确认退款</van-button>
      </div>
    </van-popup>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, onBeforeRouteLeave } from 'vue-router'
import { showToast } from 'vant'
import api from '@/api'
import { useRefresh } from '@/composables/useRefresh'
import { useContractStore } from '@/stores/contract'
import { usePropertyStore } from '@/stores/property'
import type { Settlement } from '@/types'

const route = useRoute()
const contractId = Number(route.params.id)
const s = ref<Settlement | null>(null)
const showConfirm = ref(false)
const submitting = ref(false)
const form = ref({ refund_date: new Date().toISOString().slice(0, 10), refund_method: '', remark: '' })

async function fetch() {
  // 优先重新生成（后端对未确认结算单自动删除+重建，保证数据最新）
  try {
    const { data } = await api.post(`/settlements/${contractId}`, {})
    s.value = data
    return
  } catch {
    // 已确认的结算单无法重新生成，退回到 GET
    try {
      const { data } = await api.get(`/settlements/${contractId}`)
      s.value = data
    } catch (e: any) {
      showToast(e.message || '无法获取或创建结算单')
    }
  }
}

async function confirm() {
  submitting.value = true
  try {
    const { data } = await api.post(`/settlements/${contractId}/confirm`, {
      refund_date: form.value.refund_date,
      refund_method: form.value.refund_method,
      remark: form.value.remark,
    })
    s.value = data
    showConfirm.value = false
    showToast('退款确认完成')
  } catch (e: any) {
    showToast(e.message || '确认退款失败')
  } finally {
    submitting.value = false
  }
}

const contractStore = useContractStore()
const propertyStore = usePropertyStore()
onBeforeRouteLeave(() => {
  contractStore.listStale = true
  propertyStore.listStale = true
})

useRefresh(fetch)
</script>
