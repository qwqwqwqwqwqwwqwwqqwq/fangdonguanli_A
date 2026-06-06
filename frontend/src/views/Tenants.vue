<template>
  <div class="page">
    <van-nav-bar title="租客管理" placeholder>
      <template #right>
        <van-icon name="plus" size="20" @click="$router.push('/tenants/new')" />
      </template>
    </van-nav-bar>

    <van-tabs v-model:active="activeTab" sticky offset-top="46">
      <van-tab title="在用" name="active" />
      <van-tab title="已退租" name="archived" />
    </van-tabs>

    <div v-if="loading" class="skeleton-row">
      <van-skeleton title :row="2" v-for="i in 3" :key="i" />
    </div>

    <!-- 在用租客 -->
    <template v-if="activeTab === 'active'">
      <van-swipe-cell v-for="t in activeTenants" :key="t.id_number">
        <van-cell :title="t.name" :label="tenantContractLabel(t.id_number)" is-link @click="goProfile(t.id_number)">
          <template #extra>
            <span class="text-secondary" style="font-size:11px;">{{ formatId(t.id_number) }}</span>
          </template>
        </van-cell>
        <template #right>
          <van-button square type="danger" text="删除" @click="handleDelete(t)" />
        </template>
      </van-swipe-cell>
      <div v-if="!loading && activeTenants.length === 0" class="empty-hint">暂无在用租客</div>
    </template>

    <!-- 已退租/归档 -->
    <template v-if="activeTab === 'archived'">
      <van-sticky offset-top="90">
        <van-search v-model="searchText" placeholder="搜索姓名、手机号、身份证号" shape="round" clearable />
      </van-sticky>

      <div v-if="loading" class="skeleton-row">
        <van-skeleton title :row="2" v-for="i in 3" :key="i" />
      </div>

      <template v-else>
        <div v-if="!searchText && archivedTenants.length > 0" class="archive-summary">
          共 {{ archivedTenants.length }} 人归档 · 保留150天内可查
        </div>
        <div v-if="searchText && archivedTenants.length > 0" class="archive-summary">
          找到 {{ archivedTenants.length }} 人匹配 "{{ searchText }}"
        </div>

        <van-cell v-for="t in archivedTenants" :key="t.id_number" is-link @click="goProfile(t.id_number)">
          <template #title>
            <div class="archive-cell-title">
              <span>{{ t.name }}</span>
              <span :class="['archive-tag', archiveUrgency(t)]">{{ archiveDaysText(t) }}</span>
            </div>
          </template>
          <template #label>
            <div class="archive-cell-label">
              <span>{{ formatId(t.id_number) }}</span>
              <span class="archive-dot">·</span>
              <span>{{ t.phone }}</span>
            </div>
          </template>
          <template #extra>
            <span class="archive-countdown-badge" :class="'cd-' + archiveUrgency(t)">
              {{ archiveCountdown(t) }}
            </span>
          </template>
        </van-cell>

        <div v-if="archivedTenants.length === 0" class="empty-hint">
          {{ searchText ? '未找到匹配的归档租客' : '暂无已退租归档' }}
        </div>

        <div v-if="searchLoading && archivedTenants.length > 0" class="searching-hint">
          搜索中...
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import { useTenantStore } from '@/stores/tenant'
import { useContractStore } from '@/stores/contract'
import { useRefresh } from '@/composables/useRefresh'
import api from '@/api'
import type { Tenant } from '@/types'

const router = useRouter()
const store = useTenantStore()
const contractStore = useContractStore()
const activeTab = ref('active')
const loading = ref(false)
const archivedTenants = ref<any[]>([])
const searchText = ref('')
const searchLoading = ref(false)
let debounceTimer: ReturnType<typeof setTimeout> | null = null

const activeTenants = computed(() =>
  store.list.filter(t => t.status !== '已退租')
)

const contractByTenant = computed(() => {
  const map: Record<string, { count: number; active: boolean }> = {}
  for (const c of contractStore.list) {
    if (!map[c.tenant_id_number]) map[c.tenant_id_number] = { count: 0, active: false }
    map[c.tenant_id_number].count++
    if (c.status === '已租' || c.status === '退租处理中') map[c.tenant_id_number].active = true
  }
  return map
})

function tenantContractLabel(id_number: string) {
  const tenant = store.list.find(t => t.id_number === id_number)
  const parts = ['手机: ' + (tenant?.phone || '')]
  const contract = contractStore.list.find(c => c.tenant_id_number === id_number && (c.status === '待交房' || c.status === '已租' || c.status === '退租处理中'))
  if (contract) {
    if (contract.status === '待交房') parts.push('待进房')
    else if (contract.status === '退租处理中') parts.push('退租中')
    else parts.push('在租中')
  } else if (tenant?.status === '已退租') {
    parts.push('已退租')
  }
  return parts.join(' · ')
}

function archiveDays(t: any) {
  if (!t.archived_at) return 0
  const d = new Date(t.archived_at.replace(' ', 'T'))
  return Math.floor((Date.now() - d.getTime()) / 86400000)
}

function archiveDaysText(t: any) {
  const d = archiveDays(t)
  return d === 0 ? '今天' : `${d}天前`
}

function archiveUrgency(t: any) {
  const remaining = 150 - archiveDays(t)
  if (remaining <= 15) return 'expiring'
  if (remaining <= 45) return 'warn'
  return 'safe'
}

function archiveCountdown(t: any) {
  const remaining = 150 - archiveDays(t)
  return `剩${remaining}天`
}

function formatId(id: string) {
  return id.length > 12 ? id.slice(0, 6) + '...' + id.slice(-4) : id
}

function goProfile(id: string) { router.push(`/tenants/${id}`) }

async function loadArchived(search?: string) {
  searchLoading.value = true
  if (!search) loading.value = true
  try {
    const params = search?.trim() ? { q: search.trim() } : {}
    const { data } = await api.get('/tenants/archived', { params })
    archivedTenants.value = data
  } catch {
    archivedTenants.value = []
  } finally {
    loading.value = false
    searchLoading.value = false
  }
}

async function handleDelete(t: Tenant) {
  try {
    await showConfirmDialog({ title: '确认删除', message: `确定删除 ${t.name}（${t.id_number}）吗？` })
  } catch {
    return
  }
  try {
    await store.remove(t.id_number)
    showToast('删除成功')
  } catch (e: any) {
    showToast(e.message || '删除失败')
  }
}

watch(searchText, (val) => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => { loadArchived(val) }, 300)
})

onBeforeUnmount(() => {
  if (debounceTimer) clearTimeout(debounceTimer)
})

useRefresh(() => {
  store.fetchList()
  contractStore.fetchList()
  loadArchived()
})
</script>

<style scoped>
.empty-hint {
  text-align: center;
  padding: 60px 16px;
  color: #999;
  font-size: 14px;
}

.archive-summary {
  padding: 8px 16px;
  font-size: 12px;
  color: #999;
  background: #fafafa;
}

.archive-cell-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.archive-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 99px;
  font-weight: 400;
}

.archive-tag.safe {
  color: #07c160;
  background: #e8f8ee;
}

.archive-tag.warn {
  color: #ff976a;
  background: #fff3ed;
}

.archive-tag.expiring {
  color: #ee0a24;
  background: #fde8ec;
}

.archive-cell-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #999;
}

.archive-dot {
  color: #ccc;
}

.archive-countdown-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 99px;
  font-size: 11px;
  font-weight: 500;
}

.cd-safe {
  color: #07c160;
  background: #e8f8ee;
}

.cd-warn {
  color: #ff976a;
  background: #fff3ed;
}

.cd-expiring {
  color: #ee0a24;
  background: #fde8ec;
}

.searching-hint {
  text-align: center;
  padding: 8px;
  color: #999;
  font-size: 12px;
}
</style>
