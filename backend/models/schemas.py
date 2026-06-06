"""
Pydantic v2 模型 — 请求体 / 响应体。
"""
import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List

# ============================================================
# 共享校验
# ============================================================
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_PHONE_RE = re.compile(r"^1\d{10}$")
_ID_RE = re.compile(r"^\d{17}[\dXx]$")


def _check_date(v: str) -> str:
    """校验 YYYY-MM-DD 格式 + 真实日历日期，允许 None（Optional 字段跳过）"""
    if v is None:
        return v
    if not _DATE_RE.match(v):
        raise ValueError("日期格式必须为 YYYY-MM-DD")
    try:
        from datetime import datetime
        datetime.strptime(v, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"日期 '{v}' 无效（如2月30日不存在）")
    return v


def _check_month(v: str) -> str:
    """校验 YYYY-MM 格式"""
    if not _MONTH_RE.match(v):
        raise ValueError("月份格式必须为 YYYY-MM（如 2026-05）")
    return v


def _check_phone(v: str) -> str:
    """校验中国手机号（1开头11位数字）"""
    if not _PHONE_RE.match(v):
        raise ValueError("手机号必须为 11 位数字且以 1 开头")
    return v


def _check_id_number(v: str) -> str:
    """校验18位身份证号格式"""
    if not _ID_RE.match(v):
        raise ValueError("身份证号必须为 18 位数字或末位为 X")
    return v


# ============================================================
# 租客
# ============================================================
class TenantCreate(BaseModel):
    id_number: str = Field(..., min_length=18, max_length=18)
    name: str = Field(..., min_length=1, max_length=50)
    phone: str = Field(..., min_length=11, max_length=11)
    remark: str = Field(default="", max_length=500)

    @field_validator("id_number")
    @classmethod
    def check_id_number(cls, v):
        return _check_id_number(v)

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v):
        return _check_phone(v)


class TenantUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=50)
    phone: Optional[str] = Field(default=None, min_length=11, max_length=11)
    remark: Optional[str] = Field(default=None, max_length=500)

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v):
        if v is None:
            return v
        return _check_phone(v)


class TenantResponse(BaseModel):
    id_number: str
    name: str
    phone: str
    status: str = "在用"
    remark: str = ""
    archived_at: str | None = None


class TenantCreditResponse(BaseModel):
    id_number: str
    name: str
    phone: str
    current_overdue_count: int
    has_current_overdue: str
    total_overdue_count: int


class ProfileMeterReading(BaseModel):
    reading_date: str
    current_reading: int
    consumption: int = 0
    electricity_amount: float = 0.0

class ProfileBill(BaseModel):
    bill_code: str
    bill_month: str
    rent: int
    water_fee: int
    electricity_fee: float = 0.0
    total: float = 0.0
    status: str
    paid_amount: int = 0

class ProfileMoveInInspection(BaseModel):
    inspection_date: str
    meter_base_reading: int
    key_delivery_detail: str = ""
    items: list[dict] = []

class ProfileMoveOutInspection(BaseModel):
    inspection_date: str
    meter_reading: int
    electricity_deduction: float = 0.0
    key_return_status: str
    key_deduction: int = 0
    items: list[dict] = []

class ProfileSettlement(BaseModel):
    deposit_total: int
    electricity_deduction: float = 0.0
    item_damage_deduction: int = 0
    item_missing_deduction: int = 0
    key_deduction: int = 0
    unpaid_bills_total: float = 0.0
    other_deduction: int = 0
    actual_refund: float | None = None
    refund_date: str | None = None
    refund_method: str | None = None
    settled_at: str | None = None

class ProfilePayment(BaseModel):
    payment_date: str
    total_amount: int
    payment_method: str
    remark: str = ""

class TenantProfileContract(BaseModel):
    contract_id: int
    contract_code: str
    property_name: str
    start_date: str
    end_date: str
    status: str
    days_rented: int
    total_billed: float
    total_paid: float
    has_unpaid: bool
    meter_readings: list[ProfileMeterReading] = []
    bills: list[ProfileBill] = []
    move_in_inspection: ProfileMoveInInspection | None = None
    move_out_inspection: ProfileMoveOutInspection | None = None
    settlement: ProfileSettlement | None = None
    items: list[dict] = []
    payments: list[ProfilePayment] = []


class TenantProfileResponse(BaseModel):
    id_number: str
    name: str
    phone: str
    status: str
    archived_at: str | None = None
    created_at: str = ""
    # 统计
    total_contracts: int = 0
    total_days_rented: int = 0
    total_rooms_rented: int = 0
    total_billed: float = 0.0
    total_paid: float = 0.0
    total_unpaid: float = 0.0
    overdue_count: int = 0
    # 明细
    contracts: list[TenantProfileContract] = []
    current_contract: TenantProfileContract | None = None


class CleanupResponse(BaseModel):
    removed_count: int
    message: str


# ============================================================
# 房产
# ============================================================
class PropertyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    address: str = Field(..., min_length=1, max_length=200)
    status: str = Field(default="空闲")
    remark: str = Field(default="", max_length=500)

    @field_validator("status")
    @classmethod
    def check_status(cls, v):
        if v not in ("空闲", "已租", "维修中"):
            raise ValueError("状态必须为 空闲/已租/维修中")
        return v


class PropertyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = Field(default=None, max_length=200)
    status: Optional[str] = None
    remark: Optional[str] = Field(default=None, max_length=500)

    @field_validator("status")
    @classmethod
    def check_status(cls, v):
        if v is not None and v not in ("空闲", "已租", "维修中"):
            raise ValueError("状态必须为 空闲/已租/维修中")
        return v


class PropertyResponse(BaseModel):
    id: int
    property_code: str
    name: str
    address: str
    status: str
    remark: str


# ============================================================
# 合同
# ============================================================
class ContractItemIn(BaseModel):
    item_name: str = Field(..., min_length=1, max_length=100)
    quantity: int = Field(..., gt=0)


class ContractCreate(BaseModel):
    property_id: int = Field(..., gt=0)
    tenant_id_number: str = Field(..., min_length=18, max_length=18)
    residents_count: int = Field(default=1, gt=0)
    monthly_rent: int = Field(..., ge=0)
    deposit: int = Field(..., ge=0)
    rent_due_day: int = Field(..., ge=1, le=28)
    water_fee: Optional[int] = Field(default=None, ge=0)
    start_date: str
    end_date: str
    key_count: int = Field(default=0, ge=0)
    items: List[ContractItemIn] = []
    remark: str = Field(default="", max_length=500)

    @field_validator("start_date", "end_date")
    @classmethod
    def check_date(cls, v):
        return _check_date(v)


class ContractUpdate(BaseModel):
    property_id: Optional[int] = Field(default=None, gt=0)
    tenant_id_number: Optional[str] = Field(default=None, min_length=18, max_length=18)
    residents_count: Optional[int] = Field(default=None, gt=0)
    monthly_rent: Optional[int] = Field(default=None, ge=0)
    deposit: Optional[int] = Field(default=None, ge=0)
    rent_due_day: Optional[int] = Field(default=None, ge=1, le=28)
    water_fee: Optional[int] = Field(default=None, ge=0)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    key_count: Optional[int] = Field(default=None, ge=0)
    remark: Optional[str] = Field(default=None, max_length=500)
    items: Optional[List[ContractItemIn]] = None

    @field_validator("start_date", "end_date")
    @classmethod
    def check_date(cls, v):
        return _check_date(v)


class ContractResponse(BaseModel):
    id: int
    contract_code: str
    property_id: int
    property_name: str = ""
    tenant_id_number: str
    tenant_name: str = ""
    tenant_phone: str = ""
    residents_count: int
    monthly_rent: int
    deposit: int
    payment_method: str
    rent_due_day: int
    water_fee: int
    start_date: str
    end_date: str
    key_count: int
    status: str
    remark: str
    has_pending_changes: bool = False
    pending_changes_json: Optional[str] = None
    items: List[dict] = []
    images: List[dict] = []
    created_at: str
    updated_at: str


# ============================================================
# 交房验收
# ============================================================
class MoveInInspectionCreate(BaseModel):
    contract_id: int = Field(..., gt=0)
    inspection_date: str
    meter_base_reading: int = Field(..., ge=0)
    key_delivery_detail: str = Field(default="{}", max_length=2000)

    @field_validator("inspection_date")
    @classmethod
    def check_date(cls, v):
        return _check_date(v)


class MoveInInspectionItemUpdate(BaseModel):
    status: str
    defect_remark: str = Field(default="", max_length=500)

    @field_validator("status")
    @classmethod
    def check_status(cls, v):
        if v not in ("完好", "有瑕疵"):
            raise ValueError("物品状态必须为 完好/有瑕疵")
        return v


# ============================================================
# 电表记录
# ============================================================
class MeterReadingCreate(BaseModel):
    contract_id: int = Field(..., gt=0)
    current_reading: int = Field(..., ge=0)
    reading_date: str
    remark: str = Field(default="", max_length=500)

    @field_validator("reading_date")
    @classmethod
    def check_date(cls, v):
        return _check_date(v)


class MeterReadingUpdate(BaseModel):
    current_reading: Optional[int] = Field(default=None, ge=0)
    electricity_amount: Optional[float] = Field(default=None, ge=0)
    reading_date: Optional[str] = None
    remark: Optional[str] = Field(default=None, max_length=500)

    @field_validator("reading_date")
    @classmethod
    def check_date(cls, v):
        return _check_date(v)


# ============================================================
# 账单
# ============================================================
class BillGenerateRequest(BaseModel):
    bill_month: str

    @field_validator("bill_month")
    @classmethod
    def check_month(cls, v):
        return _check_month(v)


class BillOtherFeeCreate(BaseModel):
    fee_name: str = Field(..., min_length=1, max_length=100)
    amount: int = Field(..., ge=0)
    remark: str = Field(default="", max_length=500)


# ============================================================
# 收款
# ============================================================
class PaymentCreate(BaseModel):
    bill_id: int = Field(..., gt=0)
    payment_date: str
    amount: int = Field(..., gt=0)
    payment_method: str
    remark: str = Field(default="", max_length=500)

    @field_validator("payment_date")
    @classmethod
    def check_date(cls, v):
        return _check_date(v)

    @field_validator("payment_method")
    @classmethod
    def check_method(cls, v):
        if v not in ("微信", "支付宝", "银行转账", "现金"):
            raise ValueError("收款方式必须为 微信/支付宝/银行转账/现金")
        return v


class BatchPaymentCreate(BaseModel):
    bill_ids: List[int] = Field(..., min_length=2)
    payment_date: str
    total_amount: int = Field(..., gt=0)
    payment_method: str
    remark: str = Field(default="", max_length=500)

    @field_validator("payment_date")
    @classmethod
    def check_date(cls, v):
        return _check_date(v)

    @field_validator("payment_method")
    @classmethod
    def check_method(cls, v):
        if v not in ("微信", "支付宝", "银行转账", "现金"):
            raise ValueError("收款方式必须为 微信/支付宝/银行转账/现金")
        return v


# ============================================================
# 退房验收
# ============================================================
class MoveOutInspectionCreate(BaseModel):
    contract_id: int = Field(..., gt=0)
    inspection_date: str
    meter_reading: int = Field(..., ge=0)
    electricity_deduction: float = Field(default=0.0, ge=0)
    key_return_status: str = "已归还"
    key_deduction: int = Field(default=0, ge=0)
    remark: str = Field(default="", max_length=500)

    @field_validator("inspection_date")
    @classmethod
    def check_date(cls, v):
        return _check_date(v)

    @field_validator("key_return_status")
    @classmethod
    def check_key_status(cls, v):
        if v not in ("已归还", "未归还"):
            raise ValueError("钥匙交回状态必须为 已归还/未归还")
        return v


class MoveOutInspectionItemUpdate(BaseModel):
    status: str
    deduction_amount: int = Field(default=0, ge=0)

    @field_validator("status")
    @classmethod
    def check_status(cls, v):
        if v not in ("完好", "损坏", "缺失"):
            raise ValueError("物品状态必须为 完好/损坏/缺失")
        return v


class MoveOutKeyDeductionUpdate(BaseModel):
    key_deduction: int = Field(..., ge=0)



class MoveOutInspectionUpdate(BaseModel):
    """退房验收信息编辑 — 编辑后自动重算电费并同步结算单"""
    inspection_date: Optional[str] = None
    meter_reading: Optional[int] = Field(default=None, ge=0)
    key_return_status: Optional[str] = None
    key_deduction: Optional[int] = Field(default=None, ge=0)
    remark: Optional[str] = Field(default=None, max_length=500)

    @field_validator("inspection_date")
    @classmethod
    def check_date(cls, v):
        return _check_date(v)

    @field_validator("key_return_status")
    @classmethod
    def check_key_status(cls, v):
        if v is not None and v not in ("已归还", "未归还"):
            raise ValueError("钥匙交回状态必须为 已归还/未归还")
        return v


# ============================================================
# 结算单
# ============================================================
class SettlementCreate(BaseModel):
    other_deduction: int = Field(default=0, ge=0)
    remark: str = Field(default="", max_length=500)


class SettlementConfirm(BaseModel):
    refund_date: str
    refund_method: str
    remark: str = Field(default="", max_length=500)

    @field_validator("refund_date")
    @classmethod
    def check_date(cls, v):
        return _check_date(v)

    @field_validator("refund_method")
    @classmethod
    def check_method(cls, v):
        if v not in ("微信", "支付宝", "银行转账", "现金"):
            raise ValueError("退款方式必须为 微信/支付宝/银行转账/现金")
        return v


# ============================================================
# 催收
# ============================================================
class DunningCreate(BaseModel):
    sms_content: str = Field(..., min_length=1, max_length=2000)


# ============================================================
# 通用
# ============================================================
class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None
