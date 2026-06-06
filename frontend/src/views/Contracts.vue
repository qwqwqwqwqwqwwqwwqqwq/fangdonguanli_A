<template>
  <div class="page">
    <van-nav-bar title="合同管理" placeholder>
      <template #right>
        <van-icon name="plus" size="20" @click="$router.push('/contracts/new')" />
      </template>
    </van-nav-bar>

    <van-dropdown-menu>
      <van-dropdown-item v-model="filterStatus" :options="statusOptions" @change="load" />
    </van-dropdown-menu>

    <div v-if="store.loading" class="skeleton-row">
      <van-skeleton title :row="3" v-for="i in 3" :key="i" />
    </div>

    <div v-for="c in store.list" :key="c.id" class="card" @click="$router.push(`/contracts/${c.id}`)">
      <div class="flex-between">
        <span style="font-weight:600;">{{ c.property_name }}</span>
        <span :class="'tag-' + c.status">{{ c.status }}</span>
      </div>
      <div class="flex-between mt-16" style="font-size:13px;">
        <span class="text-secondary">合同编号：{{ c.contract_code }}</span>
        <span>租客：{{ c.tenant_name }} · 手机：{{ c.tenant_phone }}</span>
      </div>
      <div class="flex-between mt-16" style="font-size:13px;color:var(--text-secondary);">
        <span>月租 ¥{{ c.monthly_rent }} · 押金 ¥{{ c.deposit }}</span>
        <span>期限：{{ c.start_date }} ~ {{ c.end_date }}</span>
      </div>
    </div>

    <div v-if="!store.loading && store.list.length === 0" class="text-secondary" style="text-align:center;padding:60px;">
      {{ filterStatus ? '暂无该状态的合同' : '暂无合同' }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { useContractStore } from '@/stores/contract'
import { useRefresh } from '@/composables/useRefresh'

const route = useRoute()
const store = useContractStore()
const filterStatus = ref((route.query.status as string) || '')

const statusOptions = [
  { text: '全部', value: '' },
  { text: '待交房', value: '待交房' },
  { text: '已租', value: '已租' },
  { text: '退租处理中', value: '退租处理中' },
]

function load() {
  store.fetchList(filterStatus.value)
}
useRefresh(() => store.ensureFresh(filterStatus.value))
</script>
