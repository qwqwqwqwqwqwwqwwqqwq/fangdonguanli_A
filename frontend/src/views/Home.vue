<template>
  <div class="page">
    <van-nav-bar title="房东管理系统" placeholder />

    <!-- 统计卡片 -->
    <div class="stat-grid">
      <div class="stat-card stat-card--danger" @click="$router.push('/bills?status=逾期')">
        <div class="stat-card__num">{{ dashboard.overdue_bill_count }}</div>
        <div class="stat-card__label">逾期账单</div>
      </div>
      <div class="stat-card stat-card--primary" @click="$router.push('/properties?status=空闲')">
        <div class="stat-card__num">{{ dashboard.vacant_count }}</div>
        <div class="stat-card__label">空置房源</div>
      </div>
      <div class="stat-card stat-card--warning" @click="goPendingRent">
        <div class="stat-card__num">¥{{ dashboard.pending_rent }}</div>
        <div class="stat-card__label">待收租金</div>
      </div>
    </div>

    <!-- 合同概览 -->
    <van-cell-group inset title="合同概览">
      <van-cell v-for="s in dashboard.contract_summary" :key="s.status" is-link @click="$router.push('/contracts?status=' + s.status)">
        <template #title>
          <span :class="'tag-' + s.status" style="font-size:14px;">{{ s.status }}</span>
        </template>
        <template #value><span style="font-weight:600;">{{ s.count }}</span> 份</template>
      </van-cell>
      <van-cell v-if="dashboard.contract_summary.length === 0" title="暂无合同" value="去创建" is-link @click="$router.push('/contracts/new')" />
    </van-cell-group>

    <!-- 快捷操作 -->
    <div style="margin:16px;">
      <van-grid :column-num="2" :border="false">
        <van-grid-item icon="description-o" text="新增合同" @click="$router.push('/contracts/new')" />
        <van-grid-item icon="records-o" text="账单管理" @click="$router.push('/bills')" />
        <van-grid-item icon="gold-coin-o" text="收款" @click="$router.push('/payments/new')" />
        <van-grid-item icon="friends-o" text="租客管理" @click="$router.push('/tenants')" />
        <van-grid-item icon="down" text="备份数据" @click="handleBackup" />
        <van-grid-item icon="up" text="恢复数据" @click="handleRestore" />
        <van-grid-item icon="bookmark-o" text="使用说明" @click="handleDownloadGuide" />
      </van-grid>

      <input ref="restoreInput" type="file" accept=".xlsx" style="display:none" @change="onFileSelected" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import api from '@/api'
import { useRefresh } from '@/composables/useRefresh'
import type { DashboardData } from '@/types'

const router = useRouter()
const dashboard = reactive<DashboardData>({ overdue_bill_count: 0, contract_summary: [], vacant_count: 0, pending_rent: 0, pending_contract_ids: [] })

useRefresh(async () => {
  const { data } = await api.get('/dashboard')
  Object.assign(dashboard, data)
})

function goPendingRent() {
  const ids = dashboard.pending_contract_ids
  if (ids && ids.length > 0) {
    router.push('/bills?contract_ids=' + ids.join(','))
  } else {
    router.push('/bills')
  }
}

const restoreInput = ref<HTMLInputElement | null>(null)
const restoring = ref(false)

async function handleBackup() {
  try {
    const res = await api.get('/backup/excel', { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    const date = new Date().toISOString().slice(0, 10).replace(/-/g, '')
    a.download = `landlord_backup_${date}.xlsx`
    a.click()
    window.URL.revokeObjectURL(url)
    showToast('备份下载中')
  } catch (e: any) {
    showToast(e.message || '备份失败')
  }
}

function handleDownloadGuide() {
  const a = document.createElement('a')
  a.href = '/guide/guide.md'
  a.download = '房东管理系统_使用说明.md'
  a.click()
}

function handleRestore() {
  showConfirmDialog({
    title: '恢复数据',
    message: '将清空当前全部数据并用 Excel 文件内容替换，此操作不可撤销。确定继续吗？',
  }).then(() => {
    restoreInput.value?.click()
  }).catch(() => {})
}

async function onFileSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  restoring.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const { data } = await api.post('/backup/restore', fd)
    showToast(data.message || '恢复成功')
    window.location.reload()
  } catch (e: any) {
    showToast(e.message || '恢复失败')
  } finally {
    restoring.value = false
    input.value = ''
  }
}
</script>
