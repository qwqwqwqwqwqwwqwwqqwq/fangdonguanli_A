<template>
  <div class="page">
    <van-nav-bar title="房产管理" placeholder>
      <template #right>
        <van-icon name="plus" size="20" @click="$router.push('/properties/new')" />
      </template>
    </van-nav-bar>

    <van-dropdown-menu>
      <van-dropdown-item v-model="filterStatus" :options="statusOptions" @change="load" />
    </van-dropdown-menu>

    <div v-if="store.loading" class="skeleton-row">
      <van-skeleton title :row="2" v-for="i in 3" :key="i" />
    </div>

    <van-swipe-cell v-for="p in store.list" :key="p.id">
      <van-cell :title="p.name" :label="p.address" is-link @click="goEdit(p.id)">
        <template #value>
          <span :class="'tag-' + p.status">{{ p.status }}</span>
        </template>
        <template #extra>
          <span class="text-secondary">{{ p.property_code }}</span>
        </template>
      </van-cell>
      <template #right>
        <van-button square type="danger" text="删除" @click="handleDelete(p)" />
      </template>
    </van-swipe-cell>

    <div v-if="!store.loading && store.list.length === 0" class="text-secondary" style="text-align:center;padding:60px;">
      <div style="font-size:40px;margin-bottom:8px;">🏠</div>
      暂无房产<br><span style="font-size:12px;">点击右上角 + 添加第一套房源</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import { usePropertyStore } from '@/stores/property'
import { useRefresh } from '@/composables/useRefresh'
import type { Property } from '@/types'

const route = useRoute()
const router = useRouter()
const store = usePropertyStore()
const filterStatus = ref((route.query.status as string) || '')

const statusOptions = [
  { text: '全部', value: '' },
  { text: '空闲', value: '空闲' },
  { text: '已租', value: '已租' },
  { text: '维修中', value: '维修中' },
]

function load() { store.fetchList(filterStatus.value) }
function goEdit(id: number) { router.push(`/properties/${id}/edit`) }

async function handleDelete(p: Property) {
  try {
    await showConfirmDialog({ title: '确认删除', message: `确定删除 ${p.name}（${p.property_code}）吗？` })
  } catch {
    return
  }
  try {
    await store.remove(p.id)
    showToast('删除成功')
  } catch (e: any) {
    showToast(e.message || '删除失败')
  }
}

useRefresh(load)
</script>
