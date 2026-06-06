<template>
  <div class="page">
    <van-nav-bar title="退房验收" left-arrow placeholder @click-left="$router.back()" />
    <div v-if="loading" class="loading"><van-loading /></div>

    <!-- 已有退房验收：显示详情 + 物品编辑 -->
    <div v-else-if="insp" style="padding-bottom:60px;">
      <van-cell-group inset title="验收信息">
        <van-cell title="验收日期" :value="insp.inspection_date" />
        <van-cell title="电表读数" :value="String(insp.meter_reading)" />
        <van-cell title="电费扣款" :value="'¥' + insp.electricity_deduction" />
        <van-cell title="钥匙归还" :value="insp.key_return_status" />
	        <van-cell title="钥匙扣款" is-link @click="insp.key_return_status === '未归还' && openKeyDeductionEdit()">
	          <template #value>
	            <span :class="insp.key_deduction > 0 ? 'text-danger' : ''">¥{{ insp.key_deduction }}</span>
	            <span v-if="insp.key_return_status === '未归还'" style="color:var(--van-primary-color);font-size:12px;"> 点击修改</span>
	          </template>
	        </van-cell>
        <van-cell v-if="insp.remark" title="备注" :value="insp.remark" />
      </van-cell-group>

      <div style="padding:8px 16px;">
        <van-button size="small" type="primary" plain @click="openEditInspection">编辑验收信息</van-button>
      </div>

      <!-- 物品清单（可编辑） -->
      <van-cell-group inset title="物品清单" class="mt-16" v-if="insp.items?.length">
        <van-cell
          v-for="item in insp.items"
          :key="item.id"
          :title="item.item_name"
          :value="item.quantity + '件'"
          is-link
          @click="openItemEdit(item)"
        >
          <template #label>
            <span :class="'tag-' + item.status">{{ item.status }}</span>
            <span v-if="item.deduction_amount > 0" style="color:#ee0a24;"> · 扣款¥{{ item.deduction_amount }}</span>
          </template>
        </van-cell>
      </van-cell-group>
      <van-empty v-else description="暂无物品记录" />
    </div>

    <!-- 无退房验收：创建入口 -->
    <div v-else style="padding:16px;">
      <van-empty description="暂无退房验收记录" />
      <van-button block type="warning" round @click="showForm = true">开始退房验收</van-button>
    </div>

    <!-- 创建退房验收 Popup -->
    <van-popup v-model:show="showForm" position="bottom" :style="{ height: '70%' }" round>
      <div style="padding:16px;">
        <h3>退房验收</h3>
        <van-field v-model="form.inspection_date" label="验收日期" type="date" placeholder="选择日期" :rules="[{ required: true }]" />
        <van-field v-model="form.meter_reading" label="电表读数（累计值）" type="number" placeholder="当前电表读数" @update:model-value="calcElectricity" />
        <van-field :model-value="estimatedElectricity" label="预计电费扣款" readonly placeholder="输入电表读数后自动计算" />
	        <van-field v-model="form.key_return_status" label="钥匙归还" readonly is-link placeholder="请选择" @click="showKeyStatusPicker = true" />
	        <van-field v-model="form.key_deduction" :label="form.key_return_status === '未归还' ? '钥匙扣款（必填）' : '钥匙扣款'" type="number" :placeholder="form.key_return_status === '已归还' ? '0（已归还无需扣款）' : '请输入扣款金额'" :readonly="form.key_return_status === '已归还'" :required="form.key_return_status === '未归还'" />
        <van-field v-model="form.remark" label="备注" placeholder="" />
        <p style="color:#999;font-size:12px;padding:8px 16px 0;">验收完成后，可在物品清单中逐项确认状态和扣款金额</p>
        <van-button block type="primary" round :loading="submitting" @click="submit" style="margin-top:12px;">确认验收</van-button>
      </div>
    </van-popup>

    <!-- 创建验收-钥匙状态选择器 -->
    <van-popup v-model:show="showKeyStatusPicker" position="bottom" round>
      <van-picker
        :columns="keyStatusOptions"
        :default-index="keyStatusOptions.findIndex((s: any) => s.value === form.key_return_status)"
        @confirm="onKeyStatusConfirm"
        @cancel="showKeyStatusPicker = false"
      />
    </van-popup>

    <!-- 物品编辑 Popup -->
    <van-popup v-model:show="showItemEdit" position="bottom" :style="{ height: '40%' }" round>
      <div style="padding:16px;" v-if="editingItem">
        <h3>{{ editingItem.item_name }}（{{ editingItem.quantity }}件）</h3>
        <van-field label="状态" readonly is-link :model-value="editingItem.status" @click="showStatusPicker = true" />
        <van-field v-model="editingItem.deduction_amount" label="扣款金额" type="number" placeholder="0" />
        <van-button block type="primary" round :loading="savingItem" @click="saveItem" style="margin-top:16px;">保存</van-button>
      </div>
    </van-popup>

    <!-- 状态选择器 -->
    <van-popup v-model:show="showStatusPicker" position="bottom" round>
      <van-picker
        :columns="statusOptions"
        :default-index="statusOptions.findIndex((s: any) => s.value === editingItem?.status)"
        @confirm="onStatusConfirm"
        @cancel="showStatusPicker = false"
      />
    </van-popup>

    <!-- 钥匙扣款编辑弹窗 -->
    <van-dialog v-model:show="showKeyDeductionEdit" title="修改钥匙扣款" show-cancel-button @confirm="saveKeyDeduction">
      <van-field v-model="keyDeductionEdit" label="扣款金额" type="number" placeholder="请输入扣款金额" style="margin:12px 0;" />
    </van-dialog>

    <!-- 编辑验收信息 Popup -->
    <van-popup v-model:show="showEditInspection" position="bottom" :style="{ height: '60%' }" round>
      <div style="padding:16px;">
        <h3>编辑验收信息</h3>
        <van-field v-model="editForm.inspection_date" label="验收日期" type="date" placeholder="选择日期" />
        <van-field v-model="editForm.meter_reading" label="电表读数（累计值）" type="number" placeholder="当前电表读数" @update:model-value="calcEditElectricity" />
        <van-field :model-value="editEstimatedElectricity" label="预计电费扣款" readonly placeholder="输入电表读数后自动计算" />
        <van-field v-model="editForm.key_return_status" label="钥匙归还" readonly is-link placeholder="请选择" @click="showEditKeyStatusPicker = true" />
        <van-field v-model="editForm.key_deduction" :label="editForm.key_return_status === '未归还' ? '钥匙扣款（必填）' : '钥匙扣款'" type="number" :placeholder="editForm.key_return_status === '已归还' ? '0（已归还无需扣款）' : '请输入扣款金额'" :readonly="editForm.key_return_status === '已归还'" :required="editForm.key_return_status === '未归还'" />
        <van-field v-model="editForm.remark" label="备注" placeholder="" />
        <van-button block type="primary" round :loading="savingInspection" @click="saveInspection" style="margin-top:12px;">保存修改</van-button>
      </div>
    </van-popup>

    <!-- 编辑验收-钥匙状态选择器 -->
    <van-popup v-model:show="showEditKeyStatusPicker" position="bottom" round>
      <van-picker
        :columns="keyStatusOptions"
        :default-index="keyStatusOptions.findIndex((s: any) => s.value === editForm.key_return_status)"
        @confirm="onEditKeyStatusConfirm"
        @cancel="showEditKeyStatusPicker = false"
      />
    </van-popup>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRoute, onBeforeRouteLeave } from 'vue-router'
import { showToast } from 'vant'
import api from '@/api'
import { useRefresh } from '@/composables/useRefresh'
import { useContractStore } from '@/stores/contract'
import type { MoveOutInspection, MoveOutInspectionItem } from '@/types'

const route = useRoute()
const contractId = Number(route.params.id)
const insp = ref<MoveOutInspection | null>(null)
const loading = ref(true)
const submitting = ref(false)
const showForm = ref(false)
const showItemEdit = ref(false)
const showStatusPicker = ref(false)
const showKeyStatusPicker = ref(false)
const savingItem = ref(false)
const lastMeterReading = ref<number | null>(null)
const estimatedElectricity = ref('')

// 监听电表读数变化，自动计算电费
async function fetchLastReading() {
  try {
    const { data } = await api.get(`/meter-readings/contracts/${contractId}/readings`)
    if (data.length > 0) {
      lastMeterReading.value = data[data.length - 1].current_reading
    } else {
      // 无抄表记录，尝试取交房底数
      try {
        const { data: mi } = await api.get(`/inspections/move-in/${contractId}`)
        lastMeterReading.value = mi.meter_base_reading
      } catch {
        lastMeterReading.value = 0
      }
    }
  } catch {
    lastMeterReading.value = 0
  }
}

function calcElectricity(reading: string) {
  const current = Number(reading)
  const last = lastMeterReading.value ?? 0
  if (current > 0 && last >= 0) {
    const deduction = Math.round((current - last) * 1.2 * 1e10) / 1e10
    estimatedElectricity.value = deduction > 0 ? '¥' + deduction : '¥' + deduction + '（读数异常）'
  } else {
    estimatedElectricity.value = ''
  }
}
const editingItem = ref<MoveOutInspectionItem | null>(null)
const statusOptions = [{ text: '完好', value: '完好' }, { text: '损坏', value: '损坏' }, { text: '缺失', value: '缺失' }]
const showKeyDeductionEdit = ref(false)
const keyDeductionEdit = ref<number>(0)

// 编辑验收信息
const showEditInspection = ref(false)
const showEditKeyStatusPicker = ref(false)
const savingInspection = ref(false)
const editEstimatedElectricity = ref('')
const keyStatusOptions = [{ text: '已归还', value: '已归还' }, { text: '未归还', value: '未归还' }]
const editForm = reactive({
  inspection_date: '',
  meter_reading: '',
  key_return_status: '已归还',
  key_deduction: '0',
  remark: '',
})

const form = ref({
  inspection_date: new Date().toISOString().slice(0, 10), meter_reading: '0', electricity_deduction: '0',
  key_return_status: '已归还', key_deduction: '0', remark: '',
})

async function fetch() {
  await fetchLastReading()
  loading.value = true
  try {
    const { data } = await api.get(`/inspections/move-out/${contractId}`)
    insp.value = data
    showForm.value = false
  } catch {
    insp.value = null
  } finally {
    loading.value = false
  }
}

async function submit() {
  submitting.value = true
  try {
    const { data } = await api.post('/inspections/move-out', {
      contract_id: contractId,
      inspection_date: form.value.inspection_date,
      meter_reading: Number(form.value.meter_reading),
      electricity_deduction: 0,
      key_return_status: form.value.key_return_status,
      key_deduction: Number(form.value.key_deduction),
      remark: form.value.remark,
    })
    insp.value = data
    showForm.value = false
    showToast('退房验收完成，请逐项确认物品状态')
  } catch (e: any) {
    showToast(e.message || '验收失败')
  } finally {
    submitting.value = false
  }
}

function openItemEdit(item: MoveOutInspectionItem) {
  editingItem.value = reactive({ ...item })
  showItemEdit.value = true
}

function onStatusConfirm({ selectedOptions }: any) {
  if (editingItem.value) {
    editingItem.value.status = selectedOptions[0]?.value || selectedOptions[0]
  }
  showStatusPicker.value = false
}

function onKeyStatusConfirm({ selectedOptions }: any) {
  form.value.key_return_status = selectedOptions[0]?.value || selectedOptions[0]
  if (form.value.key_return_status === '已归还') {
    form.value.key_deduction = '0'
  }
  showKeyStatusPicker.value = false
}

async function saveItem() {
  if (!insp.value || !editingItem.value) return
  savingItem.value = true
  try {
    const item = editingItem.value
    await api.put(`/inspections/move-out/${insp.value.id}/items/${item.id}`, {
      status: item.status,
      deduction_amount: Number(item.deduction_amount),
    })
    // 更新本地列表
    const idx = insp.value.items?.findIndex(i => i.id === item.id)
    if (idx !== undefined && idx >= 0 && insp.value.items) {
      insp.value.items[idx] = { ...item }
    }
    showItemEdit.value = false
    // 如果已有未确认的结算单，提示用户结算单已自动更新
    try {
      const { data: s } = await api.get(`/settlements/${contractId}`)
      if (s && !s.settled_at) {
        showToast('已保存，结算单已自动更新')
        return
      }
    } catch {}
    showToast('保存成功')
  } catch (e: any) {
    showToast(e.message || '保存失败')
  } finally {
    savingItem.value = false
  }
}


function openKeyDeductionEdit() {
  keyDeductionEdit.value = insp.value?.key_deduction || 0
  showKeyDeductionEdit.value = true
}

async function saveKeyDeduction() {
  if (!insp.value) return
  try {
    await api.put(`/inspections/move-out/${insp.value.id}/key-deduction`, {
      key_deduction: Number(keyDeductionEdit.value),
    })
    insp.value.key_deduction = Number(keyDeductionEdit.value)
    showToast('钥匙扣款已更新')
  } catch (e: any) {
    showToast(e.message || '更新失败')
  }
}
function openEditInspection() {
  if (!insp.value) return
  editForm.inspection_date = insp.value.inspection_date
  editForm.meter_reading = String(insp.value.meter_reading)
  editForm.key_return_status = insp.value.key_return_status
  editForm.key_deduction = String(insp.value.key_deduction)
  editForm.remark = insp.value.remark || ''
  calcEditElectricity(String(insp.value.meter_reading))
  showEditInspection.value = true
}

function calcEditElectricity(reading: string) {
  const current = Number(reading)
  const last = lastMeterReading.value ?? 0
  if (current > 0 && last >= 0) {
    const deduction = Math.round((current - last) * 1.2 * 1e10) / 1e10
    editEstimatedElectricity.value = deduction > 0 ? '¥' + deduction : '¥' + deduction + '（读数异常）'
  } else {
    editEstimatedElectricity.value = ''
  }
}

function onEditKeyStatusConfirm({ selectedOptions }: any) {
  editForm.key_return_status = selectedOptions[0]?.value || selectedOptions[0]
  if (editForm.key_return_status === '已归还') {
    editForm.key_deduction = '0'
  }
  showEditKeyStatusPicker.value = false
}

async function saveInspection() {
  if (!insp.value) return
  savingInspection.value = true
  try {
    const body: any = {}
    if (editForm.inspection_date !== insp.value.inspection_date) {
      body.inspection_date = editForm.inspection_date
    }
    if (Number(editForm.meter_reading) !== insp.value.meter_reading) {
      body.meter_reading = Number(editForm.meter_reading)
    }
    if (editForm.key_return_status !== insp.value.key_return_status) {
      body.key_return_status = editForm.key_return_status
    }
    if (Number(editForm.key_deduction) !== insp.value.key_deduction) {
      body.key_deduction = Number(editForm.key_deduction)
    }
    if (editForm.remark !== (insp.value.remark || '')) {
      body.remark = editForm.remark
    }

    if (Object.keys(body).length === 0) {
      showEditInspection.value = false
      showToast('没有修改')
      return
    }

    const { data } = await api.put(`/inspections/move-out/${insp.value.id}`, body)
    insp.value = data
    showEditInspection.value = false
    showToast('验收信息已更新')
  } catch (e: any) {
    showToast(e.message || '保存失败')
  } finally {
    savingInspection.value = false
  }
}

const contractStore = useContractStore()
onBeforeRouteLeave(() => {
  contractStore.listStale = true
})

useRefresh(fetch)
</script>
