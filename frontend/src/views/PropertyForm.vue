<template>
  <div class="page">
    <van-nav-bar :title="isEdit ? '编辑房产' : '新增房产'" left-arrow placeholder @click-left="$router.back()" />

    <van-form @submit="save">
      <van-cell-group inset title="基本信息">
        <van-field v-model="form.name" label="房产名称" placeholder="如：尚景园1栋501" required :rules="[{ required: true, message: '请输入房产名称' }]" />
        <van-field v-model="form.address" label="详细地址" placeholder="省市区+门牌号" required :rules="[{ required: true, message: '请输入详细地址' }]" />
        <van-field v-model="form.status" label="状态" :is-link="!isRented" :readonly="isRented" required @click="!isRented && (showStatusPicker = true)" />
        <van-field v-model="form.remark" label="备注" placeholder="选填" />
      </van-cell-group>

      <div style="margin: 16px;">
        <van-button round block type="primary" native-type="submit">{{ isEdit ? '保存' : '创建' }}</van-button>
      </div>
    </van-form>

    <van-popup v-model:show="showStatusPicker" position="bottom" round :style="{ height: '40%' }">
      <van-picker :columns="statusColumns" @confirm="onStatusConfirm" @cancel="showStatusPicker = false" />
    </van-popup>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { usePropertyStore } from '@/stores/property'

const route = useRoute()
const router = useRouter()
const store = usePropertyStore()
const isEdit = !!route.params.id
const showStatusPicker = ref(false)
const isRented = computed(() => isEdit && form.status === '已租')
const statusColumns = [
  { text: '空闲', value: '空闲' },
  { text: '维修中', value: '维修中' },
]

function onStatusConfirm(v: { selectedValues: string[] }) {
  form.status = v.selectedValues[0] as '空闲' | '维修中'
  showStatusPicker.value = false
}

const form = reactive({
  id: undefined as number | undefined,
  name: '',
  address: '',
  status: '空闲' as '空闲' | '维修中' | '已租',
  remark: '',
})

if (isEdit) {
  store.fetchOne(Number(route.params.id)).then((p) => {
    form.id = p.id
    form.name = p.name
    form.address = p.address
    form.status = p.status
    form.remark = p.remark
  }).catch((e: any) => {
    showToast(e.message || '加载房产信息失败')
  })
}

async function save() {
  try {
    await store.save(form)
    store.listStale = true
    showToast('保存成功')
    router.replace('/properties')
  } catch (e: any) {
    showToast(e.message || '保存失败')
  }
}
</script>
