# 房东管理系统 — 文件3 重新设计

日期: 2026-05-20
状态: 已确认

## 技术栈

| 层 | 选型 | 说明 |
|---|------|------|
| 后端框架 | Python FastAPI ≥0.110 | Service 层架构 |
| ORM | SQLAlchemy 2.x | 声明式映射，关联查询 |
| 数据库 | SQLite (WAL mode) | 单文件，复用 docs/schema.sql DDL |
| 前端框架 | Vue 3.4+ + TypeScript strict | Composition API |
| 构建 | Vite 5+ | proxy → FastAPI |
| 状态管理 | Pinia | 共享状态跨组件 |
| UI | Vant 4.x | 移动端 H5 |
| 构建 | Vite | proxy → FastAPI |

## 项目结构

```
文件3/
├── backend/
│   ├── main.py              # FastAPI + lifespan
│   ├── database.py           # engine + session factory
│   ├── models/
│   │   ├── orm.py            # 18 ORM 模型
│   │   └── schemas.py        # Pydantic v2 请求/响应
│   ├── services/             # 业务逻辑（8个）
│   ├── routes/               # 路由（8个，薄层）
│   ├── tests/
│   │   ├── test_services/
│   │   └── test_api/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── router/index.ts
│   │   ├── api/index.ts
│   │   ├── stores/           # Pinia (8个)
│   │   ├── views/            # 17 页面
│   │   ├── components/       # 公共组件
│   │   └── types/            # TS 类型
│   ├── tests/
│   └── package.json
└── docs/
    └── design.md
```

## 数据流

```
User → Vue Component → Pinia Store → API (Axios)
    → FastAPI Route → Service → SQLAlchemy → SQLite
    → Service → Route → Pydantic JSON → API → Pinia → Vue
```

## 核心改进（vs 文件2）

| 改进 | 文件2 | 文件3 |
|------|-------|-------|
| 架构 | Route 直连 DB | Route → Service → DB |
| 前端类型 | JavaScript | TypeScript strict |
| 状态管理 | reactive/ref | Pinia stores |
| 错误处理 | 丢失 status | 保留完整 error |
| 并行加载 | 串行 await | Promise.all |
| 测试 | 无 | 全量覆盖（点击组合+输入fuzz） |

## 分阶段

### Phase 1: 核心三模块
- 房产 CRUD + 预检
- 租客 CRUD + 信用档案
- 合同 CRUD + 物品清单 + 图片 + 作废 + 状态流转
- 前端: Properties, Tenants, Contracts, ContractForm, ContractDetail, Home

### Phase 2: 剩余五模块
- 交房/退房验收
- 电表抄表
- 账单生成 + 催收
- 单笔/合并收款
- 结算单 + 退款确认
- 前端: 剩余 12 页面

## 测试要求
- 每个可点击元素测试 + 全排列组合
- 每个输入框 fuzz 测试
- Backend: service 单测 + API 集成测试
- Frontend: 组件交互测试
