<template>
  <div class="page">
    <van-nav-bar :title="isEdit ? '编辑租客' : '新增租客'" left-arrow placeholder @click-left="$router.back()" />

    <van-form @submit="save">
      <van-cell-group inset title="基本信息">
        <van-field v-model="form.id_number" label="身份证号" placeholder="18位身份证号" :disabled="isEdit" required :rules="[{ required: true, message: '请输入身份证号' }, { pattern: /^\d{17}[\dXx]$/, message: '身份证号需为18位' }]" />
        <van-field v-model="form.name" label="姓名" placeholder="租客姓名" required :rules="[{ required: true, message: '请输入姓名' }]" />
        <van-field v-model="form.phone" label="手机号" placeholder="11位手机号" required :rules="[{ required: true, message: '请输入手机号' }, { pattern: /^\d{11}$/, message: '手机号需为11位数字' }]" />
        <van-field v-model="form.remark" label="备注" placeholder="选填" />
      </van-cell-group>

      <div style="margin: 16px;">
        <van-button round block type="primary" native-type="submit">{{ isEdit ? '保存' : '创建' }}</van-button>
      </div>
    </van-form>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { useTenantStore } from '@/stores/tenant'

const route = useRoute()
const router = useRouter()
const store = useTenantStore()
const isEdit = !!route.params.id

const form = reactive({
  id_number: route.params.id as string || '',
  name: '',
  phone: '',
  remark: '',
})

if (isEdit) {
  store.fetchOne(form.id_number).then((t) => {
    form.name = t.name
    form.phone = t.phone
    form.remark = t.remark
  }).catch((e: any) => {
    showToast(e.message || '加载租客信息失败')
  })
}

async function save() {
  try {
    await store.save({ ...form })
    store.listStale = true
    showToast('保存成功')
    router.replace('/tenants')
  } catch (e: any) {
    showToast(e.message || '保存失败')
  }
}
</script>
