from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException


def get_or_404(db: Session, model, id_value, name: str = "记录"):
    """Get entity by primary key or raise 404."""
    obj = db.get(model, id_value)
    if not obj:
        raise HTTPException(404, f"{name}不存在")
    return obj


def next_code(db: Session, model, code_column, prefix: str, width: int = 3) -> str:
    """Generate next sequential code like HT-2605-001."""
    max_code = db.scalar(select(func.max(code_column)))
    if not max_code:
        return f"{prefix}-{'0' * (width - 1)}1"
    num = int(max_code.replace(f"{prefix}-", "").split("-")[-1]) + 1
    return f"{prefix}-{num:0{width}d}"


def next_code_ym(db: Session, model, code_column, prefix: str, ym_str: str | None = None) -> str:
    """Generate next year-month code like HT-2605-001 or ZD-2605-001."""
    from database import beijing_now
    ym = ym_str or beijing_now().strftime("%y%m")
    max_code = db.scalar(
        select(func.max(code_column)).where(code_column.like(f"{prefix}-{ym}-%"))
    )
    if not max_code:
        return f"{prefix}-{ym}-001"
    return f"{prefix}-{ym}-{int(max_code.split('-')[-1]) + 1:03d}"


def check_status(obj, allowed: set[str], op_name: str):
    """Validate entity status allows an operation."""
    if obj.status not in allowed:
        current = getattr(obj, 'status', '未知')
        raise HTTPException(400, f'当前状态为"{current}"，无法{op_name}')


def check_unique(db: Session, model, filters: dict, name: str = "记录"):
    """Raise 400 if a matching record already exists."""
    stmt = select(model)
    for k, v in filters.items():
        stmt = stmt.where(getattr(model, k) == v)
    existing = db.scalar(stmt.limit(1))
    if existing:
        raise HTTPException(400, f"{name}已存在")
