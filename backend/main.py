"""
房东管理系统 — FastAPI 入口。
"""
from fastapi import FastAPI, Depends, Request, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from sqlalchemy import func, select
import os

from datetime import date
import shutil
import io

from database import init_db, UPLOAD_DIR, get_db, DB_PATH
from services.constants import beijing_today_str
from models.orm import Contract, Bill, Property, Tenant, PaymentAllocation

# 默认 API Key 仅用于本地开发；生产环境务必通过环境变量 API_KEY 覆盖
API_KEY = os.getenv("API_KEY", "dev-key-change-me")

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:5173",  # Vite 开发服务器
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:5173",
    # Capacitor APK (WebView 的 origin 是 capacitor://localhost)
    "capacitor://localhost",
    # 生产环境额外域名通过环境变量添加，逗号分隔
    *([o.strip() for o in os.getenv("EXTRA_ORIGINS", "").split(",") if o.strip()]),
]

SKIP_AUTH_PATHS = {"/api/health", "/docs", "/openapi.json", "/redoc"}
GUIDE_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(GUIDE_DIR, exist_ok=True)


async def verify_api_key(request: Request):
    if request.url.path in SKIP_AUTH_PATHS or request.url.path.startswith("/uploads") or request.url.path.startswith("/guide"):
        return
    key = request.headers.get("X-API-Key")
    if key != API_KEY:
        raise HTTPException(401, "无效的 API Key")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="房东管理系统 API", version="2.0.0", lifespan=lifespan, dependencies=[Depends(verify_api_key)])

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/guide", StaticFiles(directory=GUIDE_DIR), name="guide")

# 路由注册 — Phase 1
from routes.properties import router as properties_router
from routes.tenants import router as tenants_router
from routes.contracts import router as contracts_router

app.include_router(properties_router, prefix="/api/properties", tags=["房产管理"])
app.include_router(tenants_router, prefix="/api/tenants", tags=["租客管理"])
app.include_router(contracts_router, prefix="/api/contracts", tags=["合同管理"])

# 路由注册 — Phase 2
from routes.inspections import router as inspections_router
from routes.meter_readings import router as meter_readings_router
from routes.bills import router as bills_router
from routes.payments import router as payments_router
from routes.settlements import router as settlements_router

app.include_router(inspections_router, prefix="/api/inspections", tags=["验收管理"])
app.include_router(meter_readings_router, prefix="/api/meter-readings", tags=["电表记录"])
app.include_router(bills_router, prefix="/api/bills", tags=["账单管理"])
app.include_router(payments_router, prefix="/api/payments", tags=["收款管理"])
app.include_router(settlements_router, prefix="/api/settlements", tags=["结算单"])


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/dashboard")
def dashboard(db=Depends(get_db)):
    result = db.execute(
        select(func.count(Contract.id), Contract.status)
        .group_by(Contract.status)
    ).all()
    overdue = db.scalar(
        select(func.count(Bill.id)).where(
            Bill.status.in_(("未付", "部分付")),
            Bill.due_date < beijing_today_str(),
        )
    ) or 0
    vacant = db.scalar(
        select(func.count(Property.id)).where(Property.status == "空闲")
    ) or 0
    # 待收租金 = 所有未付/部分付账单的剩余金额
    pending_bills = list(db.scalars(select(Bill).where(Bill.status.in_(("未付", "部分付")))))
    pending_rent = 0
    if pending_bills:
        bill_ids = [b.id for b in pending_bills]
        alloc_rows = db.execute(
            select(PaymentAllocation.bill_id, func.coalesce(func.sum(PaymentAllocation.amount), 0))
            .where(PaymentAllocation.bill_id.in_(bill_ids)).group_by(PaymentAllocation.bill_id)
        ).all()
        alloc_sums = {row[0]: row[1] for row in alloc_rows}
        pending_rent = round(sum((b.total or 0) - alloc_sums.get(b.id, 0) for b in pending_bills), 10)
    pending_contract_ids = list(set(b.contract_id for b in pending_bills))
    return {
        "overdue_bill_count": overdue,
        "contract_summary": [{"status": r[1], "count": r[0]} for r in result],
        "vacant_count": vacant,
        "pending_rent": pending_rent,
        "pending_contract_ids": pending_contract_ids,
    }


@app.get("/api/backup")
def backup(db=Depends(get_db)):
    """一键备份数据库到 backup/ 目录。"""
    import os as _os
    backup_dir = _os.path.join(_os.path.dirname(DB_PATH), "backup")
    _os.makedirs(backup_dir, exist_ok=True)
    timestamp = date.today().strftime("%Y%m%d")
    backup_path = _os.path.join(backup_dir, f"landlord_{timestamp}.db")
    # 强制 checkpoint 后复制
    db.execute(select(1))
    db.commit()
    shutil.copy2(DB_PATH, backup_path)
    existing = sorted([f for f in _os.listdir(backup_dir) if f.endswith(".db")])
    return {"message": f"备份完成", "path": backup_path, "backups": existing}


@app.get("/api/backup/excel")
def backup_excel(db=Depends(get_db)):
    """导出全部数据为 Excel 文件。"""
    from services.excel_service import export_to_excel
    buf = export_to_excel(db)
    filename = f"landlord_backup_{date.today().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        io.BytesIO(buf.getvalue()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/backup/restore")
async def backup_restore(file: UploadFile = File(...), db=Depends(get_db)):
    """从 Excel 文件恢复数据（清空后导入）。"""
    from services.excel_service import import_from_excel
    content = await file.read()
    stats = import_from_excel(db, content)
    return {"message": f"已导入 {stats['_total']} 条记录", "tables": stats}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=True)
