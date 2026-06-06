import type { RouteRecordRaw } from 'vue-router'
import Home from '../views/Home.vue'
import Properties from '../views/Properties.vue'
import PropertyForm from '../views/PropertyForm.vue'
import Tenants from '../views/Tenants.vue'
import TenantForm from '../views/TenantForm.vue'
import TenantProfile from '../views/TenantProfile.vue'
import Contracts from '../views/Contracts.vue'
import ContractForm from '../views/ContractForm.vue'
import ContractDetail from '../views/ContractDetail.vue'
import MoveInInspection from '../views/MoveInInspection.vue'
import MoveOutInspection from '../views/MoveOutInspection.vue'
import MeterReadings from '../views/MeterReadings.vue'
import MeterReadingForm from '../views/MeterReadingForm.vue'
import Bills from '../views/Bills.vue'
import BillDetail from '../views/BillDetail.vue'
import Payments from '../views/Payments.vue'
import PaymentForm from '../views/PaymentForm.vue'
import Settlement from '../views/Settlement.vue'

const routes: RouteRecordRaw[] = [
  { path: '/', component: Home, meta: { title: '首页' } },
  { path: '/properties', component: Properties, meta: { title: '房产管理' } },
  { path: '/properties/new', component: PropertyForm, meta: { title: '新增房产' } },
  { path: '/properties/:id/edit', component: PropertyForm, meta: { title: '编辑房产' } },
  { path: '/tenants', component: Tenants, meta: { title: '租客管理' } },
  { path: '/tenants/new', component: TenantForm, meta: { title: '新增租客' } },
  { path: '/tenants/:id', component: TenantProfile, meta: { title: '租客档案' } },
  { path: '/tenants/:id/edit', component: TenantForm, meta: { title: '编辑租客' } },
  { path: '/contracts', component: Contracts, meta: { title: '合同管理' } },
  { path: '/contracts/new', component: ContractForm, meta: { title: '新增合同' } },
  { path: '/contracts/:id/edit', component: ContractForm, meta: { title: '编辑合同' } },
  { path: '/contracts/:id', component: ContractDetail, meta: { title: '合同详情' } },
  { path: '/contracts/:id/move-in', component: MoveInInspection, meta: { title: '交房验收' } },
  { path: '/contracts/:id/move-out', component: MoveOutInspection, meta: { title: '退房验收' } },
  { path: '/meter-readings', component: MeterReadings, meta: { title: '电表记录' } },
  { path: '/meter-readings/new', component: MeterReadingForm, meta: { title: '新增抄表' } },
  { path: '/meter-readings/:id/edit', component: MeterReadingForm, meta: { title: '编辑抄表' } },
  { path: '/bills', component: Bills, meta: { title: '账单管理' } },
  { path: '/bills/:id', component: BillDetail, meta: { title: '账单详情' } },
  { path: '/payments', component: Payments, meta: { title: '收款记录' } },
  { path: '/payments/new', component: PaymentForm, meta: { title: '收款' } },
  { path: '/contracts/:id/settlement', component: Settlement, meta: { title: '退租结算' } },
]

export default routes
