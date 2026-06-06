# 房东管理系统 — 文档索引

## 项目简介

房东管理系统是一个面向个人房东的移动端 H5 应用，覆盖租房业务全流程：
房产管理 → 租客管理 → 签约交房 → 日常抄表/账单/收款 → 退租结算。

## 技术栈

| 层 | 选型 | 版本 |
|---|------|------|
| 后端框架 | Python FastAPI | ≥0.110 |
| ORM | SQLAlchemy | 2.x |
| 数据库 | SQLite (WAL mode) | - |
| 前端框架 | Vue 3 + TypeScript strict | 3.4+ |
| 状态管理 | Pinia | - |
| UI 组件库 | Vant (移动端优先) | 4.x |
| 构建工具 | Vite + Capacitor (Android APK) | - |
| 云部署 | Render.com (免费) | - |

## 文档导航

| 文档 | 说明 |
|------|------|
| [design.md](design.md) | 架构设计与分阶段计划 |
| [api.md](api.md) | 完整 API 参考（9 域 + 8 业务链） |
| [database.md](database.md) | 数据库 schema（18 表 + 触发器） |
| [business-flow.md](business-flow.md) | 业务流程详解 |
| [testing.md](testing.md) | 测试策略与运行指南 |
| [deployment.md](deployment.md) | 部署与运维指南 |

## 快速开始

### 1. 安装依赖

```bash
# 后端
cd backend
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
# Windows: 双击 start.bat
# 或手动：
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8005 --reload

cd frontend
npx vite --host 0.0.0.0 --port 5173
```

### 3. 访问

| 地址 | 说明 |
|------|------|
| http://localhost:5173 | 前端页面 |
| http://localhost:8005/docs | Swagger API 文档 |
| http://localhost:8005/redoc | ReDoc API 文档 |

### 4. API Key 配置

默认 API Key 为 `dev-key-change-me`，通过环境变量覆盖：

```bash
export API_KEY=your-secret-key   # Linux/Mac
set API_KEY=your-secret-key      # Windows
```

⚠️ **生产环境必须更换默认 Key！** 详见 [deployment.md](deployment.md)。

### 5. 运行测试

```bash
cd backend
python test_all_apis.py          # API 全量测试（需先启动后端）
python audit_test.py             # 业务流程审计测试
```

## 项目结构

```
文件3/
├── backend/
│   ├── main.py                  # FastAPI 入口 + lifespan
│   ├── database.py              # Engine + Session + 文件上传
│   ├── models/
│   │   ├── orm.py               # 18 个 ORM 模型 + 触发器
│   │   └── schemas.py           # Pydantic v2 请求/响应模型
│   ├── services/                # 8 个业务逻辑模块
│   │   ├── property_service.py
│   │   ├── tenant_service.py
│   │   ├── contract_service.py
│   │   ├── inspection_service.py
│   │   ├── meter_service.py
│   │   ├── bill_service.py
│   │   ├── payment_service.py
│   │   ├── settlement_service.py
│   │   ├── excel_service.py
│   │   ├── constants.py
│   │   └── helpers.py
│   ├── routes/                  # 8 个薄路由层
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── router/index.ts      # 22 个路由
│   │   ├── api/index.ts         # Axios 实例 + 拦截器
│   │   ├── stores/              # 8 个 Pinia stores
│   │   ├── views/               # 17 个页面组件
│   │   ├── components/          # 公共组件
│   │   └── types/               # TypeScript 类型定义
│   ├── tests/
│   └── package.json
└── docs/                        # 项目文档
    ├── README.md                # 本文件
    ├── design.md                # 架构设计
    ├── api.md                   # API 文档
    ├── database.md              # 数据库文档
    ├── business-flow.md         # 业务流程
    ├── testing.md               # 测试指南
    └── deployment.md            # 部署指南
```

## 核心设计原则

1. **Service 层架构**: Route（薄层）→ Service（业务逻辑）→ SQLAlchemy（数据访问），职责分离
2. **北京时间统一**: 所有时间计算使用 UTC+8，不依赖服务器本地时区
3. **合同变更延迟生效**: 已租合同修改字段后标记 `has_pending_changes`，下次生成账单时自动应用
4. **软删除结算**: 退租后合同标记为"已结算-已退租"保留历史，租客归档 5 个月后自动清理
5. **电费自动计算**: 单价 1.2 元/度，抄表→自动更新账单，退房→自动扣款

## 部署方式

| 方式 | 说明 |
|------|------|
| **Android App** | 构建 APK 安装到手机，后端部署到 Render.com 云端 |
| **PWA（浏览器）** | Chrome 打开 → 添加到主屏幕，全屏运行 |
| **本地开发** | `start.bat` 启动前后端，localhost 访问 |

### Android APK 构建

```bash
cd frontend
# 1. 修改 .env.production 中的 VITE_API_BASE 为云端地址
# 2. 构建前端
npm run build
# 3. 同步到 Android 项目
npx cap sync android
# 4. 用 Android Studio 打开 android/ 目录 → Build → Build APK
```

详见 [android-deployment.md](android-deployment.md)

## 已知限制

- 当前数据库为 SQLite 单文件，高并发场景建议迁移至 PostgreSQL
- 文件上传存储在持久化磁盘 `/data/uploads/`，Render 免费额度 1GB
- API Key 通过 `VITE_API_KEY` 环境变量注入前端构建，生产环境务必更换
