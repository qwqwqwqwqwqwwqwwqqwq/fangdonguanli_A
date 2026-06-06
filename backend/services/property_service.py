"""
房产 Service — 业务逻辑层。
"""
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException

from models.orm import Property, Contract
from models.schemas import PropertyCreate, PropertyUpdate
from services.helpers import get_or_404, next_code

NON_TERMINAL_STATUSES = ("待交房", "已租", "退租处理中")


def _check_any_contract(db: Session, column: str, value) -> None:
    row = db.execute(
        select(Contract.contract_code).where(
            getattr(Contract, column) == value,
            Contract.status.in_(NON_TERMINAL_STATUSES),
        ).limit(1)
    ).first()
    if row:
        raise HTTPException(400, f"存在活跃合同（{row[0]}），无法删除")


def list_properties(db: Session, status: str | None = None) -> list[Property]:
    stmt = select(Property).order_by(Property.id)
    if status:
        stmt = stmt.where(Property.status == status)
    return list(db.scalars(stmt))


def get_property(db: Session, property_id: int) -> Property:
    return get_or_404(db, Property, property_id, "房产")


def create_property(db: Session, data: PropertyCreate) -> Property:
    prop = Property(
        property_code=next_code(db, Property, Property.property_code, "FJ"),
        name=data.name, address=data.address, status=data.status, remark=data.remark,
    )
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


def update_property(db: Session, property_id: int, data: PropertyUpdate) -> Property:
    prop = get_property(db, property_id)
    fields = data.model_dump(exclude_unset=True)
    if "status" in fields and prop.status == "已租" and fields["status"] != "已租":
        raise HTTPException(400, "已租状态的房产不能直接修改为空闲，请通过退租结算流程处理后系统会自动更新")
    for k, v in fields.items():
        setattr(prop, k, v)
    db.commit()
    db.refresh(prop)
    return prop


def delete_property(db: Session, property_id: int) -> None:
    prop = get_property(db, property_id)
    if prop.status == "已租":
        raise HTTPException(400, '该房产当前状态为"已租"，无法删除')
    _check_any_contract(db, "property_id", property_id)
    db.delete(prop)
    db.commit()
