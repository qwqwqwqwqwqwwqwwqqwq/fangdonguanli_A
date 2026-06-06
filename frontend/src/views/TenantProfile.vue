<template>
  <div class="page">
    <van-nav-bar title="租客档案" left-text="返回" left-arrow @click-left="$router.back()" placeholder>
      <template #right>
        <van-icon name="edit" size="20" @click="$router.push(`/tenants/${id}/edit`)" />
      </template>
    </van-nav-bar>

    <div v-if="loading" class="skeleton-row">
      <van-skeleton title :row="4" v-for="i in 3" :key="i" />
    </div>

    <template v-if="!loading && profile">
      <!-- 基本信息卡片 -->
      <div class="profile-header">
        <div class="profile-avatar">{{ profile.name?.[0] || '?' }}</div>
        <div class="profile-info">
          <div class="flex-between">
            <span class="profile-name">{{ profile.name }}</span>
            <span :class="['tag', profile.status === '已退租' ? 'tag-已退租' : 'tag-在用']">
              {{ profile.status }}
            </span>
          </div>
          <div class="text-secondary" style="font-size:12px;margin-top:4px;">
            {{ profile.phone }} · {{ formatId(profile.id_number) }}
          </div>
          <div v-if="profile.archived_at" class="archive-badge">
            已归档 {{ archiveDays }} 天 · 剩余 {{ 150 - archiveDays }} 天
          </div>
        </div>
      </div>

      <!-- 统计卡片 -->
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-value">{{ profile.total_days_rented }}</div>
          <div class="stat-label">累计租天</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ profile.total_rooms_rented }}</div>
          <div class="stat-label">租过房间</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ profile.total_contracts }}</div>
          <div class="stat-label">合同数</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ fmtYuan(profile.total_billed) }}</div>
          <div class="stat-label">总账单</div>
        </div>
        <div class="stat-card">
          <div class="stat-value success">{{ fmtYuan(profile.total_paid) }}</div>
          <div class="stat-label">已缴费</div>
        </div>
        <div class="stat-card">
          <div :class="['stat-value', profile.total_unpaid > 0 ? 'danger' : 'success']">
            {{ fmtYuan(profile.total_unpaid) }}
          </div>
          <div class="stat-label">未缴</div>
        </div>
      </div>

      <!-- 缴费进度总览 -->
      <van-cell-group title="缴费总览" inset style="margin-top:12px;">
        <div style="padding:12px 16px;">
          <div class="flex-between" style="margin-bottom:4px;">
            <span class="text-secondary" style="font-size:12px;">总缴费进度</span>
            <span style="font-size:12px;">{{ payPercent.toFixed(1) }}%</span>
          </div>
          <van-progress :percentage="payPercent" :color="payPercent >= 100 ? '#07c160' : '#ee0a24'"
            :show-pivot="false" stroke-width="8" />
          <div class="flex-between" style="margin-top:8px;">
            <span style="font-size:11px;color:#999;">已缴 {{ fmtYuan(profile.total_paid) }}</span>
            <span style="font-size:11px;color:#999;">总额 {{ fmtYuan(profile.total_billed) }}</span>
          </div>
          <div v-if="profile.overdue_count > 0" style="margin-top:6px;font-size:12px;color:#ee0a24;">
            历史逾期 {{ profile.overdue_count }} 次
          </div>
        </div>
      </van-cell-group>

      <!-- 合同历史 -->
      <van-cell-group title="租房历史" inset style="margin-top:12px;">
        <div class="timeline" v-if="profile.contracts.length > 0">
          <div class="timeline-item" v-for="c in profile.contracts" :key="c.contract_id"
            @click="$router.push(`/contracts/${c.contract_id}`)">
            <div class="timeline-dot" :class="c.status === '已租' || c.status === '退租处理中' ? 'dot-active' : 'dot-done'"></div>
            <div class="timeline-content">
              <div class="flex-between">
                <span class="timeline-title">{{ c.property_name }}</span>
                <span :class="['tag', statusTag(c.status)]">{{ c.status }}</span>
              </div>
              <div class="text-secondary" style="font-size:11px;margin:2px 0;">
                {{ c.contract_code }} · {{ c.start_date }} ~ {{ c.end_date }}（{{ c.days_rented }}天）
              </div>
              <div class="flex-between" style="margin-top:4px;">
                <span style="font-size:11px;color:#999;">
                  账单 {{ fmtYuan(c.total_billed) }} / 已缴 {{ fmtYuan(c.total_paid) }}
                </span>
                <van-tag v-if="c.has_unpaid" type="danger">有欠费</van-tag>
                <van-tag v-else type="success">已结清</van-tag>
              </div>
            </div>
          </div>
        </div>
        <van-cell v-else title="暂无租房记录" />
      </van-cell-group>

      <!-- 快速操作 -->
      <div v-if="profile.current_contract" style="padding:16px;">
        <van-button type="primary" block @click="$router.push(`/contracts/${profile.current_contract.contract_id}`)">
          查看当前合同详情
        </van-button>
      </div>

      <!-- 恢复租客按钮（仅已退租） -->
      <div v-if="profile.status === '已退租'" style="padding:0 16px 16px;">
        <van-button type="warning" block @click="handleRestore" :loading="restoring">
          恢复租客（重新激活）
        </van-button>
        <div style="font-size:11px;color:#999;text-align:center;margin-top:4px;">
          恢复后租客可重新签约，历史数据仍保留
        </div>
      </div>

      <!-- 已结算合同详情面板 -->
      <van-cell-group inset title="合同详情" style="margin-top:12px;"
        v-for="c in profile.contracts" :key="'detail-' + c.contract_id">
        <van-collapse v-if="c.status === '已结算-已退租'" v-model="collapseActive[c.contract_id]">
          <van-collapse-item name="items" title="合同物品" v-if="c.items?.length">
            <van-cell v-for="item in c.items" :key="item.item_name"
              :title="item.item_name" :value="item.quantity + '件'" />
          </van-collapse-item>

          <van-collapse-item name="move_in" title="交房验收" v-if="c.move_in_inspection">
            <van-cell title="验收日期" :value="c.move_in_inspection.inspection_date" />
            <van-cell title="电表底数" :value="String(c.move_in_inspection.meter_base_reading)" />
            <van-cell title="钥匙交付" :value="c.move_in_inspection.key_delivery_detail" />
            <van-cell v-for="item in c.move_in_inspection.items" :key="'mi-' + item.item_name"
              :title="item.item_name" :value="item.quantity + '件'">
              <template #label>{{ item.status }}<span v-if="item.defect_remark"> · {{ item.defect_remark }}</span></template>
            </van-cell>
          </van-collapse-item>

          <van-collapse-item name="move_out" title="退房验收" v-if="c.move_out_inspection">
            <van-cell title="验收日期" :value="c.move_out_inspection.inspection_date" />
            <van-cell title="电表读数" :value="String(c.move_out_inspection.meter_reading)" />
            <van-cell title="电费扣款" :value="'¥' + c.move_out_inspection.electricity_deduction" />
            <van-cell title="钥匙归还" :value="c.move_out_inspection.key_return_status" />
            <van-cell title="钥匙扣款" :value="'¥' + c.move_out_inspection.key_deduction" />
            <van-cell v-for="item in c.move_out_inspection.items" :key="'mo-' + item.item_name"
              :title="item.item_name" :value="item.quantity + '件'">
              <template #label>
                <span :class="item.status === '完好' ? 'text-success' : 'text-danger'">{{ item.status }}</span>
                <span v-if="item.deduction_amount > 0"> · 扣款¥{{ item.deduction_amount }}</span>
              </template>
            </van-cell>
          </van-collapse-item>

          <van-collapse-item name="meters" title="抄表记录" v-if="c.meter_readings?.length">
            <van-cell v-for="mr in c.meter_readings" :key="'mr-' + mr.reading_date"
              :title="mr.reading_date" :value="'¥' + mr.electricity_amount">
              <template #label>
                读数 {{ mr.current_reading }} · 用电 {{ mr.consumption }} kWh
              </template>
            </van-cell>
          </van-collapse-item>

          <van-collapse-item name="bills" title="账单记录" v-if="c.bills?.length">
            <van-cell v-for="b in c.bills" :key="'bill-' + b.bill_code"
              :title="b.bill_month + ' ' + b.bill_code" :value="'¥' + b.total">
              <template #label>
                <span>租金{{ b.rent }} + 水费{{ b.water_fee }} + 电费{{ b.electricity_fee }}</span>
                <van-tag :type="b.status === '已付' ? 'success' : b.status === '部分付' ? 'warning' : 'danger'" style="margin-left:4px;">
                  {{ b.status }}
                </van-tag>
                <span v-if="b.paid_amount > 0" style="margin-left:4px;color:#999;">已付{{ b.paid_amount }}</span>
              </template>
            </van-cell>
          </van-collapse-item>

          <van-collapse-item name="payments" title="收款记录" v-if="c.payments?.length">
            <van-cell v-for="p in c.payments" :key="'pay-' + p.payment_date + '-' + p.total_amount"
              :title="p.payment_date" :value="'¥' + p.total_amount">
              <template #label>{{ p.payment_method }}<span v-if="p.remark"> · {{ p.remark }}</span></template>
            </van-cell>
          </van-collapse-item>

          <van-collapse-item name="settlement" title="结算单" v-if="c.settlement">
            <van-cell title="押金总额" :value="'¥' + c.settlement.deposit_total" />
            <van-cell title="电费扣款" :value="'-¥' + c.settlement.electricity_deduction" />
            <van-cell title="物品损坏扣款" :value="'-¥' + c.settlement.item_damage_deduction" />
            <van-cell title="物品缺失扣款" :value="'-¥' + c.settlement.item_missing_deduction" />
            <van-cell title="钥匙扣款" :value="'-¥' + c.settlement.key_deduction" />
            <van-cell title="未付账单" :value="'-¥' + c.settlement.unpaid_bills_total" />
            <van-cell title="其他扣款" :value="'-¥' + c.settlement.other_deduction" />
            <van-cell title="实际退款" :value="'¥' + c.settlement.actual_refund">
              <template #label><span style="font-weight:bold;">实际退款</span></template>
            </van-cell>
            <van-cell v-if="c.settlement.refund_date" title="退款日期" :value="c.settlement.refund_date" />
            <van-cell v-if="c.settlement.refund_method" title="退款方式" :value="c.settlement.refund_method" />
          </van-collapse-item>
        </van-collapse>
      </van-cell-group>
    </template>

    <div v-if="!loading && !profile" class="empty-state">
      租客不存在或已被清理
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { showToast, showConfirmDialog } from 'vant'
import api from '@/api'

const route = useRoute()
const id = computed(() => route.params.id as string)
const loading = ref(true)
const profile = ref<any>(null)
const restoring = ref(false)
const collapseActive = ref<Record<number, string[]>>({})

function formatId(idNum: string) {
  return idNum?.length > 12 ? idNum.slice(0, 6) + '...' + idNum.slice(-4) : idNum || ''
}

function fmtYuan(val: number) {
  return '¥' + val
}

function statusTag(s: string) {
  const map: Record<string, string> = { '待交房': 'tag-待交房', '已租': 'tag-已租', '退租处理中': 'tag-退租处理中', '已结算-已退租': 'tag-已结算-已退租' }
  return map[s] || ''
}

const payPercent = computed(() => {
  if (!profile.value || profile.value.total_billed === 0) return 0
  const rawPay = (profile.value.total_paid / profile.value.total_billed) * 100
  return Math.round(rawPay * 10) / 10
})

const archiveDays = computed(() => {
  if (!profile.value?.archived_at) return 0
  const d = new Date(profile.value.archived_at.replace(' ', 'T'))
  return Math.floor((Date.now() - d.getTime()) / 86400000)
})

async function handleRestore() {
  try {
    await showConfirmDialog({
      title: '恢复租客',
      message: '将租客状态恢复为"在用"，历史合同数据保留。确定恢复吗？',
    })
  } catch {
    return
  }
  restoring.value = true
  try {
    const { data } = await api.post(`/tenants/${id.value}/restore`)
    showToast('租客已恢复为在用状态')
    profile.value.status = '在用'
    profile.value.archived_at = null
  } catch (e: any) {
    showToast(e.message || '恢复失败')
  } finally {
    restoring.value = false
  }
}

onMounted(async () => {
  try {
    const { data } = await api.get(`/tenants/${id.value}/profile`)
    profile.value = data
    // 初始化折叠面板状态
    const active: Record<number, string[]> = {}
    if (data.contracts) {
      for (const c of data.contracts) {
        active[c.contract_id] = []
      }
    }
    collapseActive.value = active
  } catch (e: any) {
    console.error('加载租客档案失败', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.profile-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: #fff;
  margin: 12px 16px;
  border-radius: 8px;
}
.profile-avatar {
  width: 52px; height: 52px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1989fa, #07c160);
  color: #fff;
  font-size: 22px; font-weight: bold;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.profile-info { flex: 1; min-width: 0; }
.profile-name { font-size: 18px; font-weight: 600; }
.archive-badge {
  display: inline-block;
  margin-top: 6px;
  padding: 2px 8px;
  background: #f0f6ff; color: #1989fa;
  border-radius: 99px; font-size: 11px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding: 0 16px;
}
.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 12px 8px;
  text-align: center;
}
.stat-value { font-size: 20px; font-weight: 700; }
.stat-value.success { color: #07c160; }
.stat-value.danger { color: #ee0a24; }
.stat-label { font-size: 11px; color: #999; margin-top: 2px; }

.timeline { padding: 8px 16px 16px 28px; }
.timeline-item {
  position: relative;
  padding-bottom: 16px;
  cursor: pointer;
}
.timeline-item:not(:last-child)::before {
  content: '';
  position: absolute;
  left: -18px; top: 12px;
  width: 1px;
  height: calc(100% + 16px);
  background: #e5e5e5;
}
.timeline-dot {
  position: absolute;
  left: -23px; top: 4px;
  width: 10px; height: 10px;
  border-radius: 50%;
  border: 2px solid #ddd;
  background: #fff;
}
.dot-active { border-color: #1989fa; background: #1989fa; }
.dot-done { border-color: #07c160; background: #07c160; }
.timeline-content {
  background: #fff;
  border-radius: 8px;
  padding: 12px;
}
.timeline-title { font-size: 15px; font-weight: 500; }

.empty-state {
  text-align: center;
  padding: 80px 16px;
  color: #999;
}

.tag-在用 { color: #07c160; background: #e8f8ee; }
.tag-已退租 { color: #969799; background: #f5f5f5; }
.tag-待交房 { color: #969799; background: #f5f5f5; }
.tag-退租处理中 { color: #ee0a24; background: #fde8ec; }
.tag-已结算-已退租 { color: #07c160; background: #e8f8ee; }
</style>
