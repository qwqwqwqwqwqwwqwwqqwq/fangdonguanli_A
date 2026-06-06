"""
合同 Service — 业务逻辑层。
"""
import os, shutil, uuid, json
from sqlalchemy.orm import Session, object_session
from sqlalchemy import select, func, delete
from fastapi import HTTPException, UploadFile

from database import UPLOAD_DIR, validate_upload, safe_write_upload
from models.orm import Contract, ContractItem, ContractImage, Property, Tenant, MoveOutInspection, Settlement
from models.schemas import ContractCreate, ContractUpdate, ContractItemIn
from services.helpers import get_or_404, next_code_ym

ACTIVE_STATUSES = ("待交房", "已租", "退租处理中")
NON_TERMINAL_STATUSES = ("待交房", "已租", "退租处理中")
PENDING_FIELDS = {"monthly_rent", "deposit", "rent_due_day", "water_fee",
                  "residents_count", "key_count", "start_date", "end_date", "remark"}


def _contract_to_dict(c: Contract, prop: Property | None, tenant: Tenant | None,
                      items: list[ContractItem], images: list[ContractImage]) -> dict:
    return {
        "id": c.id, "contract_code": c.contract_code,
        "property_id": c.property_id, "property_name": prop.name if prop else "",
        "tenant_id_number": c.tenant_id_number,
        "tenant_name": tenant.name if tenant else "",
        "tenant_phone": tenant.phone if tenant else "",
        "residents_count": c.residents_count, "monthly_rent": c.monthly_rent,
        "deposit": c.deposit, "payment_method": c.payment_method,
        "rent_due_day": c.rent_due_day, "water_fee": c.water_fee,
        "start_date": c.start_date, "end_date": c.end_date,
        "key_count": c.key_count, "status": c.status, "remark": c.remark,
        "has_pending_changes": bool(c.has_pending_changes),
        "pending_changes_json": c.pending_changes_json,
        "created_at": c.created_at, "updated_at": c.updated_at,
        "items": [{"id": i.id, "item_name": i.item_name, "quantity": i.quantity, "sort_order": i.sort_order}
                  for i in items],
        "images": [{"id": i.id, "image_path": i.image_path, "sort_order": i.sort_order}
                   for i in images],
    }


def _build_response(db: Session, c: Contract) -> dict:
    prop = db.get(Property, c.property_id)
    tenant = db.get(Tenant, c.tenant_id_number)
    items = list(db.scalars(
        select(ContractItem).where(ContractItem.contract_id == c.id).order_by(ContractItem.sort_order)))
    images = list(db.scalars(
        select(ContractImage).where(ContractImage.contract_id == c.id).order_by(ContractImage.sort_order)))
    return _contract_to_dict(c, prop, tenant, items, images)


def _batch_load(db: Session, contracts: list[Contract]) -> list[dict]:
    if not contracts:
        return []
    ids = [c.id for c in contracts]
    prop_map = {p.id: p for p in db.scalars(
        select(Property).where(Property.id.in_([c.property_id for c in contracts])))}
    tenant_map = {t.id_number: t for t in db.scalars(
        select(Tenant).where(Tenant.id_number.in_([c.tenant_id_number for c in contracts])))}
    items = list(db.scalars(select(ContractItem).where(ContractItem.contract_id.in_(ids))
                            .order_by(ContractItem.sort_order)))
    imgs = list(db.scalars(select(ContractImage).where(ContractImage.contract_id.in_(ids))
                           .order_by(ContractImage.sort_order)))
    item_map, img_map = {}, {}
    for it in items:
        item_map.setdefault(it.contract_id, []).append(it)
    for ig in imgs:
        img_map.setdefault(ig.contract_id, []).append(ig)
    return [_contract_to_dict(c, prop_map.get(c.property_id), tenant_map.get(c.tenant_id_number),
                               item_map.get(c.id, []), img_map.get(c.id, [])) for c in contracts]


def list_contracts(db: Session, status: str | None = None) -> list[dict]:
    stmt = select(Contract).order_by(Contract.id.desc())
    if status:
        stmt = stmt.where(Contract.status == status)
    else:
        # 默认不显示已结算的合同，数据保留在租客档案中可查
        stmt = stmt.where(Contract.status != "已结算-已退租")
    return _batch_load(db, list(db.scalars(stmt)))
def get_contract(db: Session, contract_id: int) -> dict:
    return _build_response(db, get_or_404(db, Contract, contract_id, "合同"))


def create_contract(db: Session, data: ContractCreate) -> dict:
    prop = db.get(Property, data.property_id)
    if not prop or prop.status != "空闲":
        raise HTTPException(400, "当前没有空闲房产，无法创建新合同。请先将房产状态调整为\"空闲\"")
    if not db.get(Tenant, data.tenant_id_number):
        raise HTTPException(400, "租客不存在，请先添加租客")
    if data.end_date <= data.start_date:
        raise HTTPException(400, "合同结束日期必须晚于开始日期")

    for col, val, label in [(Contract.property_id, data.property_id, "房产"),
                             (Contract.tenant_id_number, data.tenant_id_number, "租客")]:
        active = db.scalar(select(Contract.id).where(
            col == val, Contract.status.in_(NON_TERMINAL_STATUSES)).limit(1))
        if active:
            raise HTTPException(400, f"该{label}已有活跃合同（ID: {active}），无法创建新合同")

    water_fee = data.water_fee if data.water_fee is not None else (30 * data.residents_count)
    c = Contract(
        contract_code=next_code_ym(db, Contract, Contract.contract_code, "HT"),
        property_id=data.property_id, tenant_id_number=data.tenant_id_number,
        residents_count=data.residents_count, monthly_rent=data.monthly_rent, deposit=data.deposit,
        rent_due_day=data.rent_due_day, water_fee=water_fee, start_date=data.start_date,
        end_date=data.end_date, key_count=data.key_count, status="待交房", remark=data.remark,
    )
    db.add(c)
    prop.status = "已租"
    db.flush()
    for idx, item in enumerate(data.items):
        db.add(ContractItem(contract_id=c.id, item_name=item.item_name, quantity=item.quantity, sort_order=idx))
    db.commit()
    db.refresh(c)
    return _build_response(db, c)


def _apply_pending_changes(c: Contract) -> None:
    """将待生效变更应用到合同主字段及物品清单，并清除 pending 标记。"""
    if not c.has_pending_changes:
        return
    if c.pending_changes_json:
        try:
            changes = json.loads(c.pending_changes_json)
            for k, v in changes.items():
                if hasattr(c, k):
                    setattr(c, k, v)
        except (json.JSONDecodeError, TypeError):
            pass
    if c.pending_items_json:
        try:
            items_data = json.loads(c.pending_items_json)
            sess = object_session(c)
            if sess is not None:
                for oi in list(sess.scalars(
                    select(ContractItem).where(ContractItem.contract_id == c.id))):
                    sess.delete(oi)
                for idx, item in enumerate(items_data):
                    sess.add(ContractItem(contract_id=c.id, item_name=item["item_name"],
                                          quantity=item["quantity"], sort_order=idx))
        except (json.JSONDecodeError, TypeError):
            pass
    c.has_pending_changes = 0
    c.pending_changes_json = None
    c.pending_items_json = None


def update_contract(db: Session, contract_id: int, data: ContractUpdate) -> dict:
    c = get_or_404(db, Contract, contract_id, "合同")
    if c.status not in ACTIVE_STATUSES:
        raise HTTPException(400, "该合同已结算，无法编辑")

    updates = data.model_dump(exclude_unset=True)
    if "property_id" in updates and updates["property_id"] != c.property_id:
        raise HTTPException(400, "合同关联房产创建后不可变更，请作废后重新创建")
    if c.status == "已租" and "tenant_id_number" in updates and updates["tenant_id_number"] != c.tenant_id_number:
        raise HTTPException(400, "已租合同不可变更租客，请先发起退租")

    # 日期逻辑校验
    new_start = updates.get("start_date", c.start_date)
    new_end = updates.get("end_date", c.end_date)
    if new_end <= new_start:
        raise HTTPException(400, "合同结束日期必须晚于开始日期")

    items_data = updates.pop("items", None)

    if c.status == "已租":
        pending = {k: v for k, v in updates.items()
                   if k in PENDING_FIELDS and v != getattr(c, k, None)}
        if pending:
            existing = {}
            if c.pending_changes_json:
                try:
                    existing = json.loads(c.pending_changes_json)
                except (json.JSONDecodeError, TypeError):
                    pass
            existing.update(pending)
            c.pending_changes_json = json.dumps(existing, ensure_ascii=False)
            c.has_pending_changes = 1
        if items_data is not None:
            c.pending_items_json = json.dumps(items_data, ensure_ascii=False)
            c.has_pending_changes = 1
        db.commit()
        db.refresh(c)
        return _build_response(db, c)

    # 非已租合同：直接生效
    for k, v in updates.items():
        setattr(c, k, v)
    if items_data is not None:
        for oi in list(db.scalars(select(ContractItem).where(ContractItem.contract_id == contract_id))):
            db.delete(oi)
        for idx, item in enumerate(items_data):
            db.add(ContractItem(contract_id=contract_id, item_name=item["item_name"],
                                quantity=item["quantity"], sort_order=idx))
    db.commit()
    db.refresh(c)
    return _build_response(db, c)


def add_item(db: Session, contract_id: int, item: ContractItemIn) -> dict:
    c = db.get(Contract, contract_id)
    if not c or c.status not in ACTIVE_STATUSES:
        raise HTTPException(400, "合同不存在或状态不允许编辑")
    max_order = db.scalar(
        select(func.coalesce(func.max(ContractItem.sort_order), 0))
        .where(ContractItem.contract_id == contract_id))
    db.add(ContractItem(contract_id=contract_id, item_name=item.item_name,
                        quantity=item.quantity, sort_order=(max_order or 0) + 1))
    db.commit()
    return _build_response(db, c)


def delete_item(db: Session, contract_id: int, item_id: int) -> dict:
    c = db.get(Contract, contract_id)
    if not c or c.status not in ACTIVE_STATUSES:
        raise HTTPException(400, "合同不存在或状态不允许编辑")
    item = db.get(ContractItem, item_id)
    if item and item.contract_id == contract_id:
        db.delete(item)
        db.commit()
    return _build_response(db, c)


def upload_image(db: Session, contract_id: int, file: UploadFile) -> dict:
    c = get_or_404(db, Contract, contract_id, "合同")
    ext = validate_upload(file)
    filename = f"{c.contract_code}_{uuid.uuid4().hex[:8]}{ext}"
    rel = f"contracts/{filename}"
    abs_path = safe_write_upload(rel, file)
    try:
        max_order = db.scalar(
            select(func.coalesce(func.max(ContractImage.sort_order), 0))
            .where(ContractImage.contract_id == contract_id))
        db.add(ContractImage(contract_id=contract_id, image_path=rel, sort_order=(max_order or 0) + 1))
        db.commit()
    except Exception:
        os.remove(abs_path)
        raise
    return _build_response(db, c)


def delete_image(db: Session, contract_id: int, image_id: int) -> dict:
    img = db.get(ContractImage, image_id)
    if not img or img.contract_id != contract_id:
        raise HTTPException(404, "图片不存在")
    try:
        os.remove(os.path.join(UPLOAD_DIR, img.image_path))
    except FileNotFoundError:
        pass
    db.delete(img)
    db.commit()
    c = db.get(Contract, contract_id)
    return _build_response(db, c) if c else {}


def cancel_contract(db: Session, contract_id: int) -> str:
    c = get_or_404(db, Contract, contract_id, "合同")
    if c.status != "待交房":
        raise HTTPException(400, f'该合同当前状态为"{c.status}"，无法作废。仅待交房状态的合同可作废')

    # 收集关联图片，删除合同后清理文件
    image_paths = list(db.scalars(
        select(ContractImage.image_path).where(ContractImage.contract_id == contract_id)
    ))

    # 释放房产
    prop = db.get(Property, c.property_id)
    if prop and prop.status == "已租":
        other = db.scalar(select(Contract.id).where(
            Contract.property_id == c.property_id, Contract.id != c.id,
            Contract.status.in_(NON_TERMINAL_STATUSES)).limit(1))
        if not other:
            prop.status = "空闲"

    # 物理删除合同（CASCADE 清理子表）
    db.delete(c)
    db.commit()

    # 清理磁盘上的图片文件
    for path in image_paths:
        try:
            os.remove(os.path.join(UPLOAD_DIR, path))
        except FileNotFoundError:
            pass

    return "合同已删除"


def start_termination(db: Session, contract_id: int) -> str:
    c = get_or_404(db, Contract, contract_id, "合同")
    if c.status != "已租":
        raise HTTPException(400, f'该合同当前状态为"{c.status}"，无法发起退租')
    c.status = "退租处理中"
    db.commit()
    return "退租流程已发起"


def cancel_termination(db: Session, contract_id: int) -> str:
    c = get_or_404(db, Contract, contract_id, "合同")
    if c.status != "退租处理中":
        raise HTTPException(400, "该合同未处于退租处理中状态")

    # 检查是否已有已确认的结算单（已退款则不允许取消退租）
    st = db.scalar(select(Settlement).where(Settlement.contract_id == contract_id))
    if st and st.settled_at:
        raise HTTPException(400, "结算单已确认退款，无法取消退租流程")

    c.status = "已租"
    mo_insp = db.scalar(select(MoveOutInspection).where(MoveOutInspection.contract_id == contract_id))
    if mo_insp:
        db.delete(mo_insp)
    # 删除未确认的结算单，避免下次退租时冲突
    if st and not st.settled_at:
        db.delete(st)
    db.commit()
    return "退租已取消，合同恢复为已租"
