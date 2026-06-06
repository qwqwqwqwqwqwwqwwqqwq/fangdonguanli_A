<template>
  <div class="page">
    <van-nav-bar title="收款" left-arrow placeholder @click-left="$router.back()" />
    <van-form @submit="submit" style="padding:16px;">
      <van-field v-model="form.payment_date" label="收款日期" type="date" placeholder="选择日期" :rules="[{ required: true, message: '请输入收款日期' }]" />
      <van-field v-model="form.amount" label="金额" type="number" placeholder="0" :rules="amountRules">
        <template #extra>
          <span v-if="billRemaining !== null" class="text-secondary" style="font-size:12px;">待付 ¥{{ billRemaining }}</span>
        </template>
      </van-field>
      <van-field v-model="form.payment_method" label="收款方式" placeholder="微信/支付宝/银行转账/现金" is-link readonly @click="showPicker = true" :rules="[{ required: true, message: '请选择收款方式' }]" />
      <van-field v-model="form.remark" label="备注" placeholder="选填" />
      <van-field v-model="form.bill_id" label="关联账单" is-link readonly required @click="showBillPicker = true" :rules="[{ required: true, message: '请选择关联账单' }]">
        <template #input>{{ billLabel }}</template>
      </van-field>
      <div style="margin:16px 0;">
        <van-button block type="primary" round native-type="submit" :loading="submitting">确认收款</van-button>
      </div>
    </van-form>
    <van-popup v-model:show="showPicker" position="bottom" round :style="{ height: '40%' }">
      <van-picker :columns="methods" @confirm="onPickConfirm" @cancel="showPicker = false" />
    </van-popup>
    <van-popup v-model:show="showBillPicker" position="bottom" round :style="{ height: '50%' }">
      <van-picker :columns="billOptions" @confirm="onBillConfirm" @cancel="showBillPicker = false" />
    </van-popup>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import api from '@/api'

const route = useRoute()
const router = useRouter()

// 账单剩余待付金额（防浮点数精度问题）
function remaining(bill: any) {
  return Math.round((bill.total - (bill.paid_amount || 0)) * 1e10) / 1e10
}
const isBatch = ref(false)
const submitting = ref(false)
const showPicker = ref(false)
const showBillPicker = ref(false)
const billTotal = ref<number | null>(null)
const billRemaining = ref<number | null>(null)
const billOptions = ref<{ text: string; value: number }[]>([])
const billMap = ref<Record<number, { code: string; property: string; total: number; paid_amount: number }>>({})
const methods = [
  { text: '微信', value: '微信' },
  { text: '支付宝', value: '支付宝' },
  { text: '银行转账', value: '银行转账' },
  { text: '现金', value: '现金' },
]

const form = reactive({
  payment_date: new Date().toISOString().slice(0, 10),
  amount: String(route.query.amount || ''),
  payment_method: '',
  remark: '',
  bill_id: String(route.query.bill_id || ''),
})

const billLabel = computed(() => {
  const b = billMap.value[Number(form.bill_id)]
  return b ? `${b.code} - ${b.property} (待付¥${remaining(b)})` : (form.bill_id ? `账单 #${form.bill_id}` : '请选择账单')
})

async function loadBills() {
  const { data } = await api.get('/bills', { params: { status: '未付' } })
  const unpaid = data as any[]
  // Also get partially paid bills
  const { data: partial } = await api.get('/bills', { params: { status: '部分付' } })
  const all = [...unpaid, ...(partial as any[])]
  billMap.value = {}
  billOptions.value = all.map((b: any) => {
    const remaining = Math.round((b.total - (b.paid_amount || 0)) * 1e10) / 1e10
    billMap.value[b.id] = { code: b.bill_code, property: b.property_name, total: b.total, paid_amount: b.paid_amount || 0 }
    return { text: `${b.bill_code} | ${b.property_name} | ¥${remaining}`, value: b.id }
  })
  // If a bill_id was passed in via query, make sure it's included even if already paid
  if (form.bill_id && !billMap.value[Number(form.bill_id)]) {
    try {
      const { data: b } = await api.get(`/bills/${form.bill_id}`)
      billMap.value[b.id] = { code: b.bill_code, property: b.property_name, total: b.total, paid_amount: b.paid_amount || 0 }
      billOptions.value.unshift({ text: `${b.bill_code} | ${b.property_name} | ¥${remaining(b)} (当前)`, value: b.id })
    } catch {}
  }
}

function onBillConfirm(v: { selectedValues: (number | string)[] }) {
  const id = Number(v.selectedValues[0])
  form.bill_id = String(id)
  showBillPicker.value = false
  // Load remaining for the selected bill
  loadBillRemaining()
}

async function loadBillRemaining() {
  if (!form.bill_id) return
  try {
    const { data } = await api.get(`/bills/${form.bill_id}`)
    billTotal.value = data.total
    billRemaining.value = Math.round((data.total - (data.paid_amount || 0)) * 1e10) / 1e10
  } catch (e: any) {
    showToast('加载账单信息失败: ' + (e.message || '未知错误'))
  }
}

const amountRules = computed(() => {
  const rules: any[] = [{ required: true, message: '请输入金额' }]
  if (billRemaining.value !== null) {
    rules.push({
      validator: (v: string) => Number(v) > 0 || '金额必须大于0',
    })
    rules.push({
      validator: (v: string) => Number(v) <= billRemaining.value! || `金额不能超过待付 ¥${billRemaining.value}`,
    })
  }
  return rules
})

onMounted(async () => {
  await loadBills()
  if (form.bill_id) {
    await loadBillRemaining()
  }
})

function onPickConfirm(v: { selectedOptions: Array<{ text: string }> }) {
  form.payment_method = v.selectedOptions[0]?.text || ''
  showPicker.value = false
}

async function submit() {
  submitting.value = true
  try {
    await api.post('/payments/single', {
      bill_id: Number(form.bill_id),
      payment_date: form.payment_date,
      amount: Number(form.amount),
      payment_method: form.payment_method,
      remark: form.remark,
    })
    showToast('收款成功')
    router.replace(`/bills/${form.bill_id}`)
  } catch (e: any) {
    showToast(e.message || '收款失败')
  } finally {
    submitting.value = false
  }
}
</script>
