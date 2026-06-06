<template>
  <div class="page">
    <van-nav-bar title="合同详情" left-arrow placeholder @click-left="$router.back()" />

    <div v-if="fetchError" style="padding:60px 16px;text-align:center;">
      <van-empty description="加载失败" />
      <van-button type="primary" size="small" @click="fetchError=false; loadContract()" style="margin-top:12px;">重新加载</van-button>
    </div>
    <div v-else-if="!c" class="loading"><van-loading /></div>

    <div v-if="c" style="padding-bottom:60px;">
      <!-- 状态 + 操作 -->
      <div class="card">
        <div class="flex-between">
          <span style="font-size:16px;font-weight:600;">{{ c.property_name }}</span>
          <span :class="'tag-' + c.status" style="font-size:15px;">{{ c.status }}</span>
        </div>
        <div class="text-secondary" style="margin-top:4px;">合同编号：{{ c.contract_code }}</div>
      </div>

      <!-- 待生效变更提醒 -->
      <div v-if="c.has_pending_changes" style="margin:12px 16px;padding:12px;background:#fff7e6;border:1px solid #ffd666;border-radius:8px;font-size:13px;color:#ad6800;">
        此合同有修改待下月生效，进入账单管理时将自动应用变更。
      </div>

      <!-- 租客信息 -->
      <van-cell-group inset title="租客信息">
        <van-cell title="租客" :value="c.tenant_name" />
        <van-cell title="手机" :value="c.tenant_phone" />
        <van-cell title="身份证号" :value="c.tenant_id_number" />
        <van-cell title="居住人数" :value="String(c.residents_count)" />
      </van-cell-group>

      <!-- 财务信息 -->
      <van-cell-group inset title="财务信息" class="mt-16">
        <van-cell title="月租金" :value="'¥' + c.monthly_rent" />
        <van-cell title="押金" :value="'¥' + c.deposit" />
        <van-cell title="水费" :value="'¥' + c.water_fee" />
        <van-cell title="交租截止日" :value="'每月' + c.rent_due_day + '号'" />
        <van-cell title="合同期限" :value="c.start_date + ' ~ ' + c.end_date" />
      </van-cell-group>

      <!-- 物品清单 -->
      <van-cell-group inset title="物品清单" class="mt-16" v-if="c.items.length">
        <van-cell v-for="item in c.items" :key="item.id" :title="item.item_name" :value="'x' + item.quantity" />
      </van-cell-group>

      <!-- 图片 -->
      <van-cell-group inset title="合同图片" class="mt-16" v-if="c.images.length">
        <div v-for="img in c.images" :key="img.id" style="padding:8px 16px;">
          <van-image :src="'/uploads/' + img.image_path" width="80" height="80" fit="cover" radius="4" />
        </div>
      </van-cell-group>

      <!-- 操作按钮 -->
      <div style="margin: 16px;">
        <van-button v-if="c.status === '待交房' || c.status === '已租' || c.status === '退租处理中'" block type="primary" round style="margin-bottom:8px;" @click="goEdit">编辑合同</van-button>

        <van-button v-if="c.status === '待交房'" block type="primary" round style="margin-bottom:8px;" @click="$router.push(`/contracts/${c.id}/move-in`)">交房验收</van-button>

        <van-button v-if="c.status === '待交房'" block type="danger" round style="margin-bottom:8px;" @click="handleCancel">删除合同</van-button>

        <van-button v-if="c.status === '已租' || c.status === '退租处理中'" block plain type="primary" round style="margin-bottom:8px;" @click="$router.push(`/bills?contract_id=${c.id}`)">查看账单</van-button>

        <van-button v-if="c.status === '已租' || c.status === '退租处理中'" block plain type="primary" round style="margin-bottom:8px;" @click="$router.push(`/meter-readings?contract_id=${c.id}`)">电表记录</van-button>

        <van-button v-if="c.status === '已租'" block type="warning" round style="margin-bottom:8px;" @click="handleStartTerm">发起退租</van-button>

        <van-button v-if="c.status === '退租处理中'" block type="warning" round style="margin-bottom:8px;" @click="$router.push(`/contracts/${c.id}/move-out`)">退房验收</van-button>

        <van-button v-if="c.status === '退租处理中'" block type="primary" round style="margin-bottom:8px;" @click="goSettlement">生成结算单</van-button>

        <van-button v-if="c.status === '退租处理中'" block plain type="primary" round @click="handleCancelTerm">取消退租</van-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import { useContractStore } from '@/stores/contract'
import { useRefresh } from '@/composables/useRefresh'
import api from '@/api'

const route = useRoute()
const router = useRouter()
const store = useContractStore()
const c = computed(() => store.current)
const fetchError = ref(false)

function goEdit() {
  const id = route.params.id
  router.push(`/contracts/${id}/edit`)
}

async function handleCancel() {
  try {
    await showConfirmDialog({ title: '确认删除', message: '删除后合同将被永久移除，确定继续吗？' })
  } catch {
    return
  }
  try {
    await store.cancel(Number(route.params.id))
    showToast('已删除')
    router.replace('/contracts')
  } catch (e: any) {
    showToast(e.message || '操作失败')
  }
}

async function handleStartTerm() {
  try {
    await showConfirmDialog({ title: '发起退租', message: '确定发起退租吗？' })
  } catch {
    return
  }
  try {
    await store.startTermination(Number(route.params.id))
    showToast('退租已发起')
    await store.fetchOne(Number(route.params.id))
  } catch (e: any) {
    showToast(e.message || '操作失败')
  }
}

async function goSettlement() {
  try {
    await api.get(`/inspections/move-out/${route.params.id}`)
    router.push(`/contracts/${route.params.id}/settlement`)
  } catch {
    showToast('请先完成退房验收后再生成结算单')
  }
}

async function handleCancelTerm() {
  try {
    await showConfirmDialog({ title: '取消退租', message: '确定取消退租吗？合同将恢复为已租状态。' })
  } catch {
    return
  }
  try {
    await store.cancelTermination(Number(route.params.id))
    showToast('退租已取消')
    await store.fetchOne(Number(route.params.id))
  } catch (e: any) {
    showToast(e.message || '操作失败')
  }
}

async function loadContract() {
  try {
    await store.fetchOne(Number(route.params.id))
    fetchError.value = false
  } catch {
    fetchError.value = true
  }
}
useRefresh(loadContract)

// 离开详情页时，标记列表需要刷新
onBeforeRouteLeave(() => {
  store.listStale = true
})
</script>
