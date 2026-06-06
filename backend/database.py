"""
数据库连接 — SQLAlchemy 2.x engine + session。
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException, UploadFile
from datetime import datetime, timezone, timedelta
import os

# 北京时间 UTC+8，不受服务器时区影响
BEIJING_TZ = timezone(timedelta(hours=8))


def beijing_now() -> datetime:
    """返回北京时间 datetime 对象，确保跨服务器部署时间一致。"""
    return datetime.now(BEIJING_TZ)


def beijing_now_str() -> str:
    """返回北京时间格式化字符串 YYYY-MM-DD HH:MM:SS。"""
    return beijing_now().strftime("%Y-%m-%d %H:%M:%S")

# 云部署用 DATA_DIR 环境变量，本地开发用当前目录
DATA_DIR = os.getenv("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(DATA_DIR, "landlord.db")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

for sub in ["contracts", "inspections", "meter_readings", "signatures"]:
    os.makedirs(os.path.join(UPLOAD_DIR, sub), exist_ok=True)

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False, "timeout": 30},
    echo=False,
)


def validate_upload(file: UploadFile) -> str:
    """校验上传文件扩展名，返回安全扩展名。"""
    ext = os.path.splitext(file.filename or "image.jpg")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件类型: {ext}，仅允许: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
    return ext


def safe_write_upload(rel_path: str, file: UploadFile) -> str:
    """安全写入上传文件，返回绝对路径。确保目标目录存在。"""
    abs_path = os.path.join(UPLOAD_DIR, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "wb") as f:
        import shutil
        shutil.copyfileobj(file.file, f)
    return abs_path


@event.listens_for(engine, "connect")
def _on_connect(dbapi_conn, _record):
    dbapi_conn.execute("PRAGMA foreign_keys = ON")
    dbapi_conn.execute("PRAGMA journal_mode = WAL")


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    """FastAPI 依赖 — 自动关闭 session。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """幂等初始化表结构 + 数据迁移。"""
    from models.orm import Base
    Base.metadata.create_all(bind=engine)

    # 回填已有已退租租客的 archived_at（一次性数据迁移）
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(
            text("UPDATE tenants SET archived_at = updated_at "
                 "WHERE status = '已退租' AND archived_at IS NULL")
        )
        conn.commit()
        if result.rowcount:
            print(f"[init_db] 已回填 {result.rowcount} 个租客的归档时间")
