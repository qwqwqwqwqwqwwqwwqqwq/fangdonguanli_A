"""
租客管理 API — 路由层。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.schemas import (TenantCreate, TenantUpdate, TenantResponse,
                            TenantCreditResponse, TenantProfileResponse,
                            CleanupResponse, MessageResponse)
from services.tenant_service import (
    restore_tenant,list_tenants, get_tenant, create_tenant,
    update_tenant, delete_tenant, get_credit, get_tenant_profile,
    get_archived_tenants, cleanup_expired_archives)

router = APIRouter()


@router.get("", response_model=list[TenantResponse])
def _list(db: Session = Depends(get_db)):
    return list_tenants(db)


@router.post("", response_model=TenantResponse, status_code=201)
def _create(data: TenantCreate, db: Session = Depends(get_db)):
    return create_tenant(db, data)


@router.get("/archived")
def _list_archived(q: str = "", db: Session = Depends(get_db)):
    """已退租归档租客列表（5个月内），支持按姓名/手机号/身份证号搜索。"""
    return get_archived_tenants(db, q=q)


@router.post("/cleanup", response_model=CleanupResponse)
def _cleanup(db: Session = Depends(get_db)):
    """清理超过5个月的归档数据。"""
    return cleanup_expired_archives(db)


@router.post("/{id_number}/restore")
def _restore(id_number: str, db: Session = Depends(get_db)):
    """恢复已退租的租客为在用状态。"""
    return restore_tenant(db, id_number)


@router.get("/{id_number}", response_model=TenantResponse)
def _get(id_number: str, db: Session = Depends(get_db)):
    return get_tenant(db, id_number)


@router.put("/{id_number}", response_model=TenantResponse)
def _update(id_number: str, data: TenantUpdate, db: Session = Depends(get_db)):
    return update_tenant(db, id_number, data)


@router.delete("/{id_number}", response_model=MessageResponse)
def _delete(id_number: str, db: Session = Depends(get_db)):
    delete_tenant(db, id_number)
    return {"message": "删除成功"}


@router.get("/{id_number}/profile", response_model=TenantProfileResponse)
def _profile(id_number: str, db: Session = Depends(get_db)):
    """租客完整档案：个人信息 + 合同历史 + 账单统计。"""
    return get_tenant_profile(db, id_number)


@router.get("/{id_number}/credit", response_model=TenantCreditResponse)
def _credit(id_number: str, db: Session = Depends(get_db)):
    return get_credit(db, id_number)
