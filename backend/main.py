"""
房东管理系统 — FastAPI 入口。
"""
from fastapi import FastAPI, Depends, Request, HTTPException, UploadFile, File, APIRouter
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
from models.orm import Contract, Bill, Property, PaymentAllocation

# 默认 API Key 仅用于本地开发；生产环境务必通过环境变量 API_KEY 覆盖
API_KEY = os.getenv("API_KEY", "dev-key-change-me")

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:5173",
    "capacitor://localhost",
    *([o.strip() for o in os.getenv("EXTRA_ORIGINS", "").split(",") if o.strip()]),
]

# 预计算目录真实路径（避免每个请求重复调用 realpath）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GUIDE_DIR = os.path.join(BASE_DIR, "static")
FRONTEND_DIR = os.path.join(BASE_DIR, "static-frontend")
REAL_UPLOAD_DIR = os.path.realpath(UPLOAD_DIR)
REAL_GUIDE_DIR = os.path.realpath(GUIDE_DIR)
REAL_FRONTEND_DIR = os.path.realpath(FRONTEND_DIR)
os.makedirs(GUIDE_DIR, exist_ok=True)


async def verify_api_key(request: Request):
    """API 路由专用认证依赖。"""
    if request.headers.get("X-API-Key") != API_KEY:
        raise HTTPException(401, "无效的 API Key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="房东管理系统 API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Router（带认证，health 除外） ──
api_router = APIRouter(dependencies=[Depends(verify_api_key)])

@api_router.get("/health")
def health():
    return {"status": "ok"}

@api_router.get("/dashboard")
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

@api_router.get("/backup")
def backup(db=Depends(get_db)):
    """一键备份数据库到 backup/ 目录。"""
    backup_dir = os.path.join(os.path.dirname(DB_PATH), "backup")
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = date.today().strftime("%Y%m%d")
    backup_path = os.path.join(backup_dir, f"landlord_{timestamp}.db")
    db.execute(select(1))
    db.commit()
    shutil.copy2(DB_PATH, backup_path)
    existing = sorted([f for f in os.listdir(backup_dir) if f.endswith(".db")])
    return {"message": f"备份完成", "path": backup_path, "backups": existing}

@api_router.get("/backup/excel")
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

@api_router.post("/backup/restore")
async def backup_restore(file: UploadFile = File(...), db=Depends(get_db)):
    """从 Excel 文件恢复数据（清空后导入）。"""
    from services.excel_service import import_from_excel
    content = await file.read()
    stats = import_from_excel(db, content)
    return {"message": f"已导入 {stats['_total']} 条记录", "tables": stats}

# 注册领域路由到 API Router
from routes.properties import router as properties_router
from routes.tenants import router as tenants_router
from routes.contracts import router as contracts_router
from routes.inspections import router as inspections_router
from routes.meter_readings import router as meter_readings_router
from routes.bills import router as bills_router
from routes.payments import router as payments_router
from routes.settlements import router as settlements_router

api_router.include_router(properties_router, prefix="/properties", tags=["房产管理"])
api_router.include_router(tenants_router, prefix="/tenants", tags=["租客管理"])
api_router.include_router(contracts_router, prefix="/contracts", tags=["合同管理"])
api_router.include_router(inspections_router, prefix="/inspections", tags=["验收管理"])
api_router.include_router(meter_readings_router, prefix="/meter-readings", tags=["电表记录"])
api_router.include_router(bills_router, prefix="/bills", tags=["账单管理"])
api_router.include_router(payments_router, prefix="/payments", tags=["收款管理"])
api_router.include_router(settlements_router, prefix="/settlements", tags=["结算单"])

app.include_router(api_router, prefix="/api")

# ── 静态文件挂载（按优先级：具体路径在前，SPA 兜底在最后） ──
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/guide", StaticFiles(directory=GUIDE_DIR), name="guide")

if os.path.isdir(FRONTEND_DIR):
    # StaticFiles(html=True) 自动处理 SPA 回退：找不到文件 → 返回 index.html
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="spa")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=True)
