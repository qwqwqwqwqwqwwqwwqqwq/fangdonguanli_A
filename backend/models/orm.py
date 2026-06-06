"""
SQLAlchemy ORM 模型 — 18 表 + 2 视图 + 1 触发器。
基于 docs/schema.sql 完整 DDL。
"""
from sqlalchemy import (
    Column, Integer, Float, Text, ForeignKey, CheckConstraint, UniqueConstraint,
    Index, event,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from database import beijing_now_str


class Base(DeclarativeBase):
    pass


# ============================================================
# 1. 租客
# ============================================================
class Tenant(Base):
    __tablename__ = "tenants"
    id_number = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    phone = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="在用")  # 在用 / 已退租
    archived_at = Column(Text, nullable=True)  # 退租归档时间，NULL=未归档
    remark = Column(Text, default="")
    created_at = Column(Text, nullable=False, default=lambda: beijing_now_str())
    updated_at = Column(Text, nullable=False, default=lambda: beijing_now_str())

    contracts = relationship("Contract", back_populates="tenant")


# ============================================================
# 2. 房产
# ============================================================
class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (
        CheckConstraint("status IN ('空闲', '已租', '维修中')", name="chk_property_status"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    property_code = Column(Text, nullable=False, unique=True)
    name = Column(Text, nullable=False)
    address = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="空闲")
    remark = Column(Text, default="")
    created_at = Column(Text, nullable=False, default=lambda: beijing_now_str())
    updated_at = Column(Text, nullable=False, default=lambda: beijing_now_str())

    contracts = relationship("Contract", back_populates="property")


# ============================================================
# 3. 合同
# ============================================================
class Contract(Base):
    __tablename__ = "contracts"
    __table_args__ = (
        CheckConstraint("residents_count > 0", name="chk_contract_residents"),
        CheckConstraint("monthly_rent >= 0", name="chk_contract_rent"),
        CheckConstraint("deposit >= 0", name="chk_contract_deposit"),
        CheckConstraint("rent_due_day BETWEEN 1 AND 28", name="chk_contract_due_day"),
        CheckConstraint(
            "status IN ('待交房', '已租', '退租处理中', '已结算-已退租')",
            name="chk_contract_status",
        ),
        Index("idx_contracts_property", "property_id"),
        Index("idx_contracts_tenant", "tenant_id_number"),
        Index("idx_contracts_status", "status"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_code = Column(Text, nullable=False, unique=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    tenant_id_number = Column(Text, ForeignKey("tenants.id_number"), nullable=False)
    residents_count = Column(Integer, nullable=False, default=1)
    monthly_rent = Column(Integer, nullable=False)
    deposit = Column(Integer, nullable=False)
    payment_method = Column(Text, nullable=False, default="月付")
    rent_due_day = Column(Integer, nullable=False)
    water_fee = Column(Integer, nullable=False, default=0)
    start_date = Column(Text, nullable=False)
    end_date = Column(Text, nullable=False)
    key_count = Column(Integer, nullable=False, default=0)
    status = Column(Text, nullable=False, default="待交房")
    remark = Column(Text, default="")
    has_pending_changes = Column(Integer, nullable=False, default=0)  # 0/1
    pending_changes_json = Column(Text, nullable=True)  # JSON of fields to apply next billing cycle
    pending_items_json = Column(Text, nullable=True)  # JSON of pending items changes
    created_at = Column(Text, nullable=False, default=lambda: beijing_now_str())
    updated_at = Column(Text, nullable=False, default=lambda: beijing_now_str())

    property = relationship("Property", back_populates="contracts")
    tenant = relationship("Tenant", back_populates="contracts")
    items = relationship("ContractItem", back_populates="contract", cascade="all, delete-orphan")
    images = relationship("ContractImage", back_populates="contract", cascade="all, delete-orphan")
    move_in_inspection = relationship("MoveInInspection", back_populates="contract", uselist=False, cascade="all, delete-orphan")
    meter_readings = relationship("MeterReading", back_populates="contract")
    bills = relationship("Bill", back_populates="contract")
    move_out_inspection = relationship("MoveOutInspection", back_populates="contract")
    settlement = relationship("Settlement", back_populates="contract", uselist=False)


# ============================================================
# 4. 合同物品清单
# ============================================================
class ContractItem(Base):
    __tablename__ = "contract_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_contract_item_qty"),
        Index("idx_contract_items_contract", "contract_id"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    item_name = Column(Text, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    sort_order = Column(Integer, nullable=False, default=0)

    contract = relationship("Contract", back_populates="items")


# ============================================================
# 5. 合同图片
# ============================================================
class ContractImage(Base):
    __tablename__ = "contract_images"
    __table_args__ = (
        Index("idx_contract_images_contract", "contract_id"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    image_path = Column(Text, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)

    contract = relationship("Contract", back_populates="images")


# ============================================================
# 6. 交房验收
# ============================================================
class MoveInInspection(Base):
    __tablename__ = "move_in_inspections"
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, unique=True)
    inspection_date = Column(Text, nullable=False)
    meter_base_reading = Column(Integer, nullable=False)
    key_delivery_detail = Column(Text, nullable=False, default="{}")
    meter_photo_path = Column(Text)
    landlord_signature_path = Column(Text)
    tenant_signature_path = Column(Text)
    created_at = Column(Text, nullable=False, default=lambda: beijing_now_str())

    contract = relationship("Contract", back_populates="move_in_inspection")
    items = relationship("MoveInInspectionItem", back_populates="inspection", cascade="all, delete-orphan")
    images = relationship("MoveInInspectionImage", back_populates="inspection", cascade="all, delete-orphan")


# ============================================================
# 7. 交房验收物品明细
# ============================================================
class MoveInInspectionItem(Base):
    __tablename__ = "move_in_inspection_items"
    __table_args__ = (
        CheckConstraint("status IN ('完好', '有瑕疵')", name="chk_move_in_item_status"),
        Index("idx_move_in_items_inspection", "inspection_id"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    inspection_id = Column(Integer, ForeignKey("move_in_inspections.id", ondelete="CASCADE"), nullable=False)
    item_name = Column(Text, nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(Text, nullable=False, default="完好")
    defect_remark = Column(Text, default="")

    inspection = relationship("MoveInInspection", back_populates="items")


# ============================================================
# 8. 交房验收物品照片
# ============================================================
class MoveInInspectionImage(Base):
    __tablename__ = "move_in_inspection_images"
    __table_args__ = (
        Index("idx_move_in_images_inspection", "inspection_id"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    inspection_id = Column(Integer, ForeignKey("move_in_inspections.id", ondelete="CASCADE"), nullable=False)
    image_path = Column(Text, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)

    inspection = relationship("MoveInInspection", back_populates="images")


# ============================================================
# 9. 电表记录
# ============================================================
class MeterReading(Base):
    __tablename__ = "meter_readings"
    __table_args__ = (
        Index("idx_meter_readings_contract", "contract_id"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    record_code = Column(Text, nullable=False, unique=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    last_reading = Column(Integer)
    current_reading = Column(Integer, nullable=False)
    consumption = Column(Float, nullable=True)
    electricity_amount = Column(Float, nullable=False, default=0.0)
    reading_date = Column(Text, nullable=False)
    meter_photo_path = Column(Text)
    remark = Column(Text, default="")
    created_at = Column(Text, nullable=False, default=lambda: beijing_now_str())

    contract = relationship("Contract", back_populates="meter_readings")


# ============================================================
# 10. 账单
# ============================================================
class Bill(Base):
    __tablename__ = "bills"
    __table_args__ = (
        CheckConstraint("status IN ('未付', '已付', '部分付')", name="chk_bill_status"),
        UniqueConstraint("contract_id", "bill_month"),
        Index("idx_bills_contract", "contract_id"),
        Index("idx_bills_month", "bill_month"),
        Index("idx_bills_status", "status"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    bill_code = Column(Text, nullable=False, unique=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    bill_month = Column(Text, nullable=False)
    rent = Column(Integer, nullable=False)
    water_fee = Column(Integer, nullable=False, default=0)
    electricity_fee = Column(Float, nullable=False, default=0.0)
    total = Column(Float, nullable=False, default=0.0)
    generated_date = Column(Text, nullable=False)
    due_date = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="未付")
    remark = Column(Text, default="")
    created_at = Column(Text, nullable=False, default=lambda: beijing_now_str())

    contract = relationship("Contract", back_populates="bills")
    other_fees = relationship("BillOtherFee", back_populates="bill", cascade="all, delete-orphan")
    dunning_logs = relationship("DunningLog", back_populates="bill")
    allocations = relationship("PaymentAllocation", back_populates="bill")


# ============================================================
# 11. 账单其他费用
# ============================================================
class BillOtherFee(Base):
    __tablename__ = "bill_other_fees"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="chk_other_fee_amount"),
        UniqueConstraint("bill_id", "fee_name"),
        Index("idx_bill_other_fees_bill", "bill_id"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    bill_id = Column(Integer, ForeignKey("bills.id", ondelete="CASCADE"), nullable=False)
    fee_name = Column(Text, nullable=False)
    amount = Column(Integer, nullable=False)
    remark = Column(Text, default="")

    bill = relationship("Bill", back_populates="other_fees")


# ============================================================
# 12. 收款
# ============================================================
class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("total_amount > 0", name="chk_payment_amount"),
        CheckConstraint("payment_method IN ('微信', '支付宝', '银行转账', '现金')", name="chk_payment_method"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_date = Column(Text, nullable=False)
    total_amount = Column(Integer, nullable=False)
    payment_method = Column(Text, nullable=False)
    remark = Column(Text, default="")
    created_at = Column(Text, nullable=False, default=lambda: beijing_now_str())

    allocations = relationship("PaymentAllocation", back_populates="payment", cascade="all, delete-orphan")


# ============================================================
# 13. 收款分摊
# ============================================================
class PaymentAllocation(Base):
    __tablename__ = "payment_allocations"
    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_allocation_amount"),
        UniqueConstraint("payment_id", "bill_id"),
        Index("idx_payment_allocations_payment", "payment_id"),
        Index("idx_payment_allocations_bill", "bill_id"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_id = Column(Integer, ForeignKey("payments.id", ondelete="CASCADE"), nullable=False)
    bill_id = Column(Integer, ForeignKey("bills.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Integer, nullable=False)

    payment = relationship("Payment", back_populates="allocations")
    bill = relationship("Bill", back_populates="allocations")


# ============================================================
# 14. 催收日志
# ============================================================
class DunningLog(Base):
    __tablename__ = "dunning_logs"
    __table_args__ = (
        Index("idx_dunning_logs_bill", "bill_id"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    bill_id = Column(Integer, ForeignKey("bills.id", ondelete="CASCADE"), nullable=False)
    dunning_time = Column(Text, nullable=False, default=lambda: beijing_now_str())
    sms_content = Column(Text, nullable=False)

    bill = relationship("Bill", back_populates="dunning_logs")


# ============================================================
# 15. 退房验收
# ============================================================
class MoveOutInspection(Base):
    __tablename__ = "move_out_inspections"
    __table_args__ = (
        Index("idx_move_out_inspections_contract", "contract_id"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    inspection_date = Column(Text, nullable=False)
    meter_reading = Column(Integer, nullable=False)
    electricity_deduction = Column(Float, nullable=False, default=0.0)
    key_return_status = Column(Text, nullable=False, default="已归还")
    key_deduction = Column(Integer, nullable=False, default=0)
    remark = Column(Text, default="")
    created_at = Column(Text, nullable=False, default=lambda: beijing_now_str())

    contract = relationship("Contract", back_populates="move_out_inspection")
    items = relationship("MoveOutInspectionItem", back_populates="inspection", cascade="all, delete-orphan")
    images = relationship("MoveOutInspectionImage", back_populates="inspection", cascade="all, delete-orphan")


# ============================================================
# 16. 退房验收物品明细
# ============================================================
class MoveOutInspectionItem(Base):
    __tablename__ = "move_out_inspection_items"
    __table_args__ = (
        CheckConstraint("status IN ('完好', '损坏', '缺失')", name="chk_move_out_item_status"),
        Index("idx_move_out_items_inspection", "inspection_id"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    inspection_id = Column(Integer, ForeignKey("move_out_inspections.id", ondelete="CASCADE"), nullable=False)
    item_name = Column(Text, nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(Text, nullable=False, default="完好")
    deduction_amount = Column(Integer, nullable=False, default=0)

    inspection = relationship("MoveOutInspection", back_populates="items")


# ============================================================
# 17. 退房验收房屋照片
# ============================================================
class MoveOutInspectionImage(Base):
    __tablename__ = "move_out_inspection_images"
    __table_args__ = (
        Index("idx_move_out_images_inspection", "inspection_id"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    inspection_id = Column(Integer, ForeignKey("move_out_inspections.id", ondelete="CASCADE"), nullable=False)
    image_path = Column(Text, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)

    inspection = relationship("MoveOutInspection", back_populates="images")


# ============================================================
# 18. 结算单
# ============================================================
class Settlement(Base):
    __tablename__ = "settlements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, unique=True)
    deposit_total = Column(Integer, nullable=False)
    electricity_deduction = Column(Float, nullable=False, default=0.0)
    item_damage_deduction = Column(Integer, nullable=False, default=0)
    item_missing_deduction = Column(Integer, nullable=False, default=0)
    key_deduction = Column(Integer, nullable=False, default=0)
    unpaid_bills_note = Column(Text, default="")
    unpaid_bills_total = Column(Integer, nullable=False, default=0)
    other_deduction = Column(Integer, nullable=False, default=0)
    actual_refund = Column(Integer, nullable=True)
    refund_date = Column(Text)
    refund_method = Column(Text)
    settled_at = Column(Text, nullable=True)  # 确认结算时间，NULL=未确认
    remark = Column(Text, default="")
    created_at = Column(Text, nullable=False, default=lambda: beijing_now_str())

    contract = relationship("Contract", back_populates="settlement")


# ============================================================
# 触发器：更新时自动维护 updated_at
# ============================================================
def _touch_updated_at(target) -> None:
    target.updated_at = beijing_now_str()


@event.listens_for(Contract, "before_update", propagate=True)
def _trg_contract_updated_at(_mapper, _connection, target: Contract) -> None:
    _touch_updated_at(target)


@event.listens_for(Tenant, "before_update", propagate=True)
def _trg_tenant_updated_at(_mapper, _connection, target: Tenant) -> None:
    _touch_updated_at(target)


@event.listens_for(Property, "before_update", propagate=True)
def _trg_property_updated_at(_mapper, _connection, target: Property) -> None:
    _touch_updated_at(target)
