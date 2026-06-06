// API response types matching backend Pydantic schemas

export interface Tenant {
  id_number: string
  name: string
  phone: string
  status: string
  remark: string
}

export interface TenantCredit extends Tenant {
  current_overdue_count: number
  has_current_overdue: string
  total_overdue_count: number
}

export interface Property {
  id: number
  property_code: string
  name: string
  address: string
  status: '空闲' | '已租' | '维修中'
  remark: string
}

export interface ContractItem {
  id: number
  item_name: string
  quantity: number
  sort_order: number
}

export interface ContractImage {
  id: number
  image_path: string
  sort_order: number
}

export interface Contract {
  id: number
  contract_code: string
  property_id: number
  property_name: string
  tenant_id_number: string
  tenant_name: string
  tenant_phone: string
  residents_count: number
  monthly_rent: number
  deposit: number
  payment_method: string
  rent_due_day: number
  water_fee: number
  start_date: string
  end_date: string
  key_count: number
  status: ContractStatus
  remark: string
  has_pending_changes: boolean
  pending_changes_json: string | null
  items: ContractItem[]
  images: ContractImage[]
  created_at: string
  updated_at: string
}

export type ContractStatus = '待交房' | '已租' | '退租处理中' | '已结算-已退租'

export interface MeterReading {
  id: number
  record_code: string
  contract_id: number
  last_reading: number | null
  current_reading: number
  consumption: number | null
  electricity_amount: number
  reading_date: string
  meter_photo_path: string | null
  remark: string
  created_at: string
  warning?: string
}

export type BillStatus = '未付' | '已付' | '部分付'

export interface Bill {
  id: number
  bill_code: string
  contract_id: number
  contract_code: string
  property_name: string
  tenant_name: string
  tenant_phone: string
  bill_month: string
  rent: number
  water_fee: number
  electricity_fee: number
  other_fee: number
  total: number
  paid_amount: number
  generated_date: string
  due_date: string
  status: BillStatus
  remark: string
  other_fees?: BillOtherFee[]
  created_at: string
}

export interface BillOtherFee {
  id: number
  bill_id: number
  fee_name: string
  amount: number
  remark: string
}

export interface BillPaymentRecord {
  id: number
  payment_date: string
  amount: number
  total_amount: number
  payment_method: string
  remark: string
  created_at: string
}

export interface Payment {
  id: number
  payment_date: string
  total_amount: number
  payment_method: '微信' | '支付宝' | '银行转账' | '现金'
  remark: string
  allocations?: PaymentAllocation[]
  created_at: string
}

export interface PaymentAllocation {
  id: number
  payment_id: number
  bill_id: number
  bill_code?: string
  contract_code?: string
  amount: number
}

export interface MoveInInspection {
  id: number
  contract_id: number
  inspection_date: string
  meter_base_reading: number
  key_delivery_detail: string
  meter_photo_path: string | null
  landlord_signature_path: string | null
  tenant_signature_path: string | null
  created_at: string
  items?: MoveInInspectionItem[]
  images?: MoveInInspectionImage[]
}

export interface MoveInInspectionItem {
  id: number
  inspection_id: number
  item_name: string
  quantity: number
  status: '完好' | '有瑕疵'
  defect_remark: string
}

export interface MoveInInspectionImage {
  id: number
  image_path: string
  sort_order: number
}

export interface MoveOutInspection {
  id: number
  contract_id: number
  inspection_date: string
  meter_reading: number
  electricity_deduction: number
  key_return_status: string
  key_deduction: number
  remark: string
  created_at: string
  items?: MoveOutInspectionItem[]
  images?: MoveOutInspectionImage[]
}

export interface MoveOutInspectionItem {
  id: number
  item_name: string
  quantity: number
  status: '完好' | '损坏' | '缺失'
  deduction_amount: number
}

export interface MoveOutInspectionImage {
  id: number
  image_path: string
  sort_order: number
}

export interface Settlement {
  id: number
  contract_id: number
  deposit_total: number
  electricity_deduction: number
  item_damage_deduction: number
  item_missing_deduction: number
  key_deduction: number
  unpaid_bills_note: string
  unpaid_bills_total: number
  other_deduction: number
  actual_refund: number
  refund_date: string | null
  refund_method: string | null
  remark: string
  created_at: string
}

export interface DunningLog {
  id: number
  bill_id: number
  dunning_time: string
  sms_content: string
}

export interface DashboardData {
  overdue_bill_count: number
  contract_summary: { status: string; count: number }[]
  vacant_count: number
  pending_rent: number
  pending_contract_ids?: number[]
}
