<template>
  <div class="page">
    <van-nav-bar :title="isEdit ? '编辑合同' : '新增合同'" left-arrow placeholder @click-left="$router.back()" />

    <div v-if="isEditLocked" style="margin:12px 16px;padding:12px;background:#fff7e6;border:1px solid #ffd666;border-radius:8px;font-size:13px;color:#ad6800;">
      已租合同修改不会立即生效，将在下次进入账单管理时自动同步。
    </div>

    <van-form @submit="save">
      <van-cell-group inset title="基本信息">
        <van-field v-model="form.property_id" label="关联房产" :is-link="!isEditLocked" :readonly="isEditLocked" required @click="!isEditLocked && (showPropPicker = true)">
          <template #input>{{ propLabel }}</template>
        </van-field>
        <van-field v-model="form.tenant_id_number" label="租客" :is-link="!isEditLocked" :readonly="isEditLocked" required @click="!isEditLocked && (showTenantPicker = true)">
          <template #input>{{ tenantLabel }}</template>
        </van-field>
        <van-field v-model="form.monthly_rent" label="月租金" type="number" placeholder="整数" required />
        <van-field v-model="form.deposit" label="押金" type="number" placeholder="通常1个月租金" required />
        <van-field v-model="form.rent_due_day" label="交租截止日" type="digit" placeholder="1-28" required />
        <van-field v-model="form.residents_count" label="居住人数" type="digit" placeholder="默认1" />
        <van-field v-model="form.water_fee" label="水费" type="number" placeholder="30×居住人数" />
        <van-field v-model="form.key_count" label="钥匙数量" type="digit" placeholder="0" />
        <van-field v-model="form.start_date" label="开始日期" type="date" placeholder="选择日期" />
        <van-field v-model="form.end_date" label="结束日期" type="date" placeholder="选择日期" />
        <van-field v-model="form.remark" label="备注" placeholder="特殊约定" />
      </van-cell-group>

      <van-cell-group inset title="物品清单" class="mt-16">
        <div v-for="(item, i) in form.items" :key="i" class="flex-between card" style="margin:8px 16px; padding:10px;">
          <span>{{ item.item_name }} × {{ item.quantity }}</span>
          <van-button size="mini" type="danger" @click="form.items.splice(i, 1)">删除</van-button>
        </div>
        <div style="padding: 12px 16px;">
          <van-button size="small" type="primary" plain @click="showItemAdd = true">＋ 添加物品</van-button>
        </div>
      </van-cell-group>

      <div style="margin: 16px;">
        <van-button round block type="primary" native-type="submit">{{ isEdit ? '保存' : '创建合同' }}</van-button>
      </div>
    </van-form>

    <van-popup v-model:show="showPropPicker" position="bottom" round :style="{ height: '40%' }">
      <van-picker :columns="propOptions" @confirm="onPropConfirm" @cancel="showPropPicker = false" />
    </van-popup>

    <van-popup v-model:show="showTenantPicker" position="bottom" round :style="{ height: '40%' }">
      <van-picker :columns="tenantOptions" @confirm="onTenantConfirm" @cancel="showTenantPicker = false" />
    </van-popup>

    <van-dialog v-model:show="showItemAdd" title="添加物品" show-cancel-button @confirm="addItem">
      <van-field v-model="newItemName" label="物品名称" placeholder="如：床" style="margin-top:12px;" />
      <van-field v-model="newItemQty" label="数量" type="digit" placeholder="1" />
    </van-dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { useContractStore } from '@/stores/contract'
import api from '@/api'

const route = useRoute()
const router = useRouter()
const isEdit = !!route.params.id
const contractStatus = ref('')
const isEditLocked = computed(() => isEdit && contractStatus.value === '已租')
const showPropPicker = ref(false)
const showTenantPicker = ref(false)
const showItemAdd = ref(false)
const newItemName = ref('')
const newItemQty = ref(1)
const propOptions = ref<{ text: string; value: number }[]>([])
const propMap = ref<Record<number, { name: string; property_code: string }>>({})
const tenantOptions = ref<{ text: string; value: string }[]>([])
const tenantMap = ref<Record<string, { name: string; phone: string }>>({})

const form = reactive({
  id: undefined as number | undefined,
  property_id: 0,
  tenant_id_number: '',
  residents_count: 1,
  monthly_rent: 0,
  deposit: 0,
  rent_due_day: 5,
  water_fee: 30,
  start_date: new Date().toISOString().slice(0, 10),
  end_date: (() => { const d = new Date(); d.setFullYear(d.getFullYear() + 1); return d.toISOString().slice(0, 10); })(),
  key_count: 0,
  remark: '',
  items: [] as { item_name: string; quantity: number }[],
})

let autoWaterFee = 30

const propLabel = computed(() => {
  const p = propMap.value[form.property_id]
  return p ? `${p.name} (${p.property_code})` : '请选择'
})

const tenantLabel = computed(() => {
  const t = tenantMap.value[form.tenant_id_number]
  return t ? `${t.name} (${form.tenant_id_number})` : '请选择'
})

async function loadFormData() {
  // Load all data in parallel, then cross-reference to filter both pickers
  const [{ data: properties }, { data: tenants }, { data: contracts }] = await Promise.all([
    api.get('/properties', { params: isEdit ? {} : { status: '空闲' } }),
    api.get('/tenants'),
    api.get('/contracts'),
  ])

  const activeStatuses = ['待交房', '已租', '退租处理中']
  const otherActiveContracts = (contracts as any[]).filter(
    (c: any) => activeStatuses.includes(c.status) && (!isEdit || c.id !== Number(route.params.id)),
  )
  const activePropIds = new Set(otherActiveContracts.map((c: any) => c.property_id))
  const activeTenantIds = new Set(otherActiveContracts.map((c: any) => c.tenant_id_number))

  propMap.value = {}
  propOptions.value = (properties as any[])
    .filter((p: any) => !activePropIds.has(p.id))
    .map((p: { id: number; name: string; property_code: string; status: string }) => {
      propMap.value[p.id] = { name: p.name, property_code: p.property_code }
      return { text: `${p.name} (${p.property_code})`, value: p.id }
    })

  tenantMap.value = {}
  tenantOptions.value = (tenants as any[])
    .filter((t: any) => t.status === "在用" && !activeTenantIds.has(t.id_number))
    .map((t: { id_number: string; name: string; phone: string }) => {
      tenantMap.value[t.id_number] = { name: t.name, phone: t.phone }
      return { text: `${t.name} (${t.id_number})`, value: t.id_number }
    })
}

function onPropConfirm(v: { selectedValues: (number | string)[] }) {
  form.property_id = v.selectedValues[0] as number
  showPropPicker.value = false
}

function onTenantConfirm(v: { selectedValues: (number | string)[] }) {
  form.tenant_id_number = v.selectedValues[0] as string
  showTenantPicker.value = false
}

function addItem() {
  if (!newItemName.value.trim()) return
  const qty = Number(newItemQty.value)
  if (!qty || qty < 1) { showToast('数量至少为1'); return }
  form.items.push({ item_name: newItemName.value.trim(), quantity: qty })
  newItemName.value = ''
  newItemQty.value = 1
}

watch(() => form.residents_count, (val, oldVal) => {
  const count = Number(val) || 1
  const expectedOld = 30 * (Number(oldVal) || 1)
  if (form.water_fee === autoWaterFee || form.water_fee === expectedOld) {
    autoWaterFee = 30 * count
    form.water_fee = autoWaterFee
  }
})

const store = useContractStore()

if (isEdit) {
  Promise.all([
    store.fetchOne(Number(route.params.id)).then((c) => {
      form.id = c.id
      form.property_id = c.property_id
      form.tenant_id_number = c.tenant_id_number
      form.residents_count = c.residents_count
      form.monthly_rent = c.monthly_rent
      form.deposit = c.deposit
      form.rent_due_day = c.rent_due_day
      form.water_fee = c.water_fee
      form.start_date = c.start_date
      form.end_date = c.end_date
      form.key_count = c.key_count
      form.remark = c.remark
      form.items = c.items.map((i: any) => ({ item_name: i.item_name, quantity: i.quantity }))
      autoWaterFee = c.water_fee
      contractStatus.value = c.status
      // Redirect if contract is settled/archived
      if (c.status === '已结算-已退租') {
        showToast('已结算合同不可编辑')
        router.replace('/contracts/' + c.id)
        return
      }
    }),
    loadFormData(),
  ]).catch((e: any) => {
    showToast(e.message || '加载合同信息失败')
  })
} else {
  loadFormData()
}

function validate() {
  if (!form.property_id) return '请选择关联房产'
  if (!form.tenant_id_number) return '请输入租客身份证号'
  if (Number(form.monthly_rent) < 0) return '月租金不能为负数'
  if (Number(form.deposit) < 0) return '押金不能为负数'
  const dueDay = Number(form.rent_due_day)
  if (!dueDay || dueDay < 1 || dueDay > 28) return '交租截止日必须在1-28之间'
  if (Number(form.residents_count) < 1) return '居住人数至少为1'
  if (!form.start_date) return '请填写合同开始日期'
  if (!form.end_date) return '请填写合同结束日期'
  if (form.end_date <= form.start_date) return '合同结束日期必须晚于开始日期'
  return null
}

async function save() {
  const err = validate()
  if (err) { showToast(err); return }
  try {
    const saved = await store.save({ ...form }) as { id: number }
    store.listStale = true
    if (isEdit && contractStatus.value === '已租') {
      showToast('修改已保存，将于下月交租截止日自动生效')
    } else {
      showToast('保存成功')
    }
    router.replace(`/contracts/${saved.id}`)
  } catch (e: any) {
    showToast(e.message || '保存失败')
  }
}
</script>
