# 部署与运维指南

## 环境要求

| 组件 | 最低版本 | 推荐版本 |
|------|----------|----------|
| Python | 3.10 | 3.12+ |
| Node.js | 18 | 20+ |
| npm | 9 | 10+ |
| 操作系统 | Windows 10 / Linux / macOS | - |

## 开发环境部署

### 1. 克隆仓库

```bash
git clone git@github.com:qwqwqwqwqwqwwqwwqqwq/fang_don_xi_ton.git
cd fang_don_xi_ton
```

### 2. 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows
pip install -r requirements.txt

# 启动
python -m uvicorn main:app --host 0.0.0.0 --port 8005 --reload
```

### 3. 前端

```bash
cd frontend
npm install
npx vite --host 0.0.0.0 --port 5173
```

### 4. 快捷启动

Windows 下双击 `start.bat` 同时启动前后端。

---

## 生产环境部署

### ⚠️ 安全清单

**部署前必须完成以下配置：**

- [ ] **更换 API Key**: 设置环境变量 `API_KEY` 为强随机字符串
  ```bash
  # 生成随机 Key
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- [ ] **前端移除硬编码 Key**: 将 `frontend/src/api/index.ts` 中的硬编码替换为环境变量
  ```typescript
  // 修改为
  config.headers['X-API-Key'] = import.meta.env.VITE_API_KEY
  ```
- [ ] **启用 HTTPS**: 使用 Nginx/Caddy 反向代理 + Let's Encrypt 证书
- [ ] **配置防火墙**: 仅开放 443 端口，8005 只监听本地
- [ ] **备份数据库**: 部署前执行 `GET /api/backup`

### Nginx 反向代理配置

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # 前端
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:8005;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 使用 systemd 管理后端

```ini
# /etc/systemd/system/landlord.service
[Unit]
Description=Landlord Management System
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/landlord/backend
Environment="API_KEY=your-production-key-here"
ExecStart=/opt/landlord/backend/venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8005
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now landlord.service
```

### 构建前端

```bash
cd frontend
npm run build        # 输出到 dist/
# 部署 dist/ 到静态服务器
```

---

## 数据库运维

### 备份

```bash
# 方式1: API 备份
curl -H "X-API-Key: your-key" http://localhost:8005/api/backup

# 方式2: 手动复制
cp backend/landlord.db backend/backup/landlord_$(date +%Y%m%d).db

# 方式3: Excel 导出
curl -H "X-API-Key: your-key" http://localhost:8005/api/backup/excel -o backup.xlsx
```

### 恢复

```bash
# Excel 恢复
curl -X POST -H "X-API-Key: your-key" \
  -F "file=@backup.xlsx" \
  http://localhost:8005/api/backup/restore
```

### WAL 文件管理

SQLite WAL 模式下会产生 `-wal` 和 `-shm` 文件：
- 正常关闭应用时会自动合并到主数据库
- 备份时应确保 WAL 已 checkpoint：在备份前调用 `/api/backup`（内部执行 `db.commit()`）
- 如 WAL 文件过大，可手动 checkpoint：
  ```bash
  sqlite3 backend/landlord.db "PRAGMA wal_checkpoint(TRUNCATE);"
  ```

---

## 启动/停止

### Windows (start.bat / stop.bat)

```batch
# 启动
start.bat

# 停止
stop.bat
```

> ⚠️ **已知问题**: 当前 stop.bat 查找的端口 (8002/3000) 与 start.bat 启动端口 (8005/5173) 不匹配。需要用以下命令手动停止：
> ```batch
> taskkill /f /im python.exe /fi "WINDOWTITLE eq Backend*"
> taskkill /f /im node.exe /fi "WINDOWTITLE eq Frontend*"
> ```

### Linux/Mac

```bash
# 启动
cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8005 &
cd frontend && npx vite --host 0.0.0.0 --port 5173 &

# 停止
pkill -f "uvicorn main:app"
pkill -f "vite"
```

---

## 监控

### 健康检查

```bash
curl http://localhost:8005/api/health
# 预期: {"status":"ok"}
```

### 仪表盘指标

`GET /api/dashboard` 返回:
- `overdue_bill_count` - 逾期账单数
- `vacant_count` - 空置房源数
- `pending_rent` - 待收租金总额

### 日志

后端日志输出到 stdout，包括：
- uvicorn 请求日志
- 数据库迁移日志 `[init_db]`

---

## 迁移到 PostgreSQL

如需支持更高并发，迁移步骤：

1. 安装 `psycopg2-binary`
2. 修改 `database.py` 中的 `create_engine`:
   ```python
   engine = create_engine(
       "postgresql://user:pass@localhost/landlord",
       echo=False,
   )
   ```
3. 移除 `connect_args` (SQLite 专用)
4. 导出 Excel → 导入新数据库

---

## 故障排除

| 问题 | 解决方案 |
|------|----------|
| 401 Unauthorized | 检查 Header `X-API-Key` 是否匹配 |
| 422 Unprocessable Entity | 查看 `detail` 中的字段校验错误 |
| `no such table` | 未初始化数据库，检查 `init_db()` 是否执行 |
| WAL 文件无限增长 | 执行 `PRAGMA wal_checkpoint(TRUNCATE)` |
| CORS 错误 | 确认前端 origin 在 `ALLOWED_ORIGINS` 列表中 |
| 端口占用 | `netstat -ano | findstr :8005` 查看占用进程 |
