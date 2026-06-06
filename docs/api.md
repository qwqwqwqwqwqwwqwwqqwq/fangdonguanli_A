# API 文档

## 基础信息

- **Base URL**: `http://localhost:8005/api`
- **认证方式**: Header `X-API-Key: <your-key>`
- **默认 Key**: `dev-key-change-me`（通过环境变量 `API_KEY` 覆盖）
- **免认证路径**: `/api/health`, `/docs`, `/openapi.json`, `/redoc`, `/uploads/*`, `/guide/*`
- **Content-Type**: `application/json; charset=utf-8`

## 通用响应格式

### 成功

```json
// 单条: 返回资源对象
{ "id": 1, "name": "...", ... }

// 列表: 返回数组
[{ "id": 1, ... }, { "id": 2, ... }]

// 操作: 返回 MessageResponse
{ "message": "操作成功", "detail": "可选详情" }
```

### 错误

```json
// 业务错误 (400)
{ "detail": "错误描述" }

// 校验错误 (422)
{ "detail": [{ "type": "value_error", "loc": ["body", "字段名"], "msg": "错误详情" }] }

// 认证错误 (401)
{ "detail": "无效的 API Key" }

// 未找到 (404)
{ "detail": "资源名不存在" }
```

---

## 域1: 房产管理 `/api/properties`

### POST `/api/properties` — 创建房产

```json
// Request
{ "name": "阳光花园A栋101", "address": "北京市朝阳区", "status": "空闲", "remark": "" }

// Response 201
{ "id": 1, "property_code": "FJ-001", "name": "...", "address": "...", "status": "空闲", "remark": "" }
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string(1-100) | ✅ | 房产名称 |
| address | string(1-200) | ✅ | 地址 |
| status | enum | ❌ | 空闲(默认)/已租/维修中 |
| remark | string(0-500) | ❌ | 备注 |

### GET `/api/properties` — 房产列表

`?status=空闲` 按状态筛选。默认返回全部。

### GET `/api/properties/{id}` — 房产详情

### PUT `/api/properties/{id}` — 编辑房产

⚠️ 已租状态的房产不能直接改为空闲，需通过退租结算流程。

### DELETE `/api/properties/{id}` — 删除房产

⚠️ 仅空闲且无活跃合同的房产可删除。

---

## 域2: 租客管理 `/api/tenants`

### POST `/api/tenants` — 创建租客

```json
// Request
{ "id_number": "110101199001011234", "name": "张伟", "phone": "13800138001", "remark": "" }

// Response 201
{ "id_number": "110101199001011234", "name": "张伟", "phone": "13800138001", "status": "在用", "archived_at": null }
```

| 字段 | 类型 | 必填 | 校验 |
|------|------|------|------|
| id_number | string(18) | ✅ | 18位身份证号，末位可为X |
| name | string(1-50) | ✅ | 姓名 |
| phone | string(11) | ✅ | 1开头11位数字 |
| remark | string(0-500) | ❌ | 备注 |

### GET `/api/tenants` — 租客列表

### GET `/api/tenants/{id_number}` — 租客详情

### PUT `/api/tenants/{id_number}` — 编辑租客

### DELETE `/api/tenants/{id_number}` — 删除租客

⚠️ 有活跃合同的租客无法删除。

### GET `/api/tenants/{id_number}/profile` — 租客完整档案

返回历史合同、账单缴费统计、电表记录、验收记录、结算记录。

```json
{
  "id_number": "...", "name": "...", "status": "在用",
  "total_contracts": 2, "total_days_rented": 730,
  "total_billed": 50000.0, "total_paid": 48000.0,
  "total_unpaid": 2000.0, "overdue_count": 1,
  "contracts": [{ "contract_id": 1, "bills": [...], "meter_readings": [...], ... }],
  "current_contract": { ... }
}
```

### GET `/api/tenants/{id_number}/credit` — 租客征信

```json
{ "current_overdue_count": 1, "has_current_overdue": "是", "total_overdue_count": 3 }
```

### GET `/api/tenants/archived?q=` — 已退租归档查询

支持按姓名/手机号/身份证号搜索，仅返回归档不超过 5 个月的租客。

### POST `/api/tenants/cleanup` — 清理超期归档

删除归档超过 5 个月的租客及其关联合同、账单等数据。

### POST `/api/tenants/{id_number}/restore` — 恢复已退租租客

---

## 域3: 合同管理 `/api/contracts`

### POST `/api/contracts` — 创建合同

```json
// Request
{
  "property_id": 1, "tenant_id_number": "110101199001011234",
  "monthly_rent": 2000, "deposit": 2000, "rent_due_day": 5,
  "residents_count": 2, "water_fee": 60, "key_count": 2,
  "start_date": "2026-01-01", "end_date": "2026-12-31",
  "items": [{ "item_name": "空调", "quantity": 2 }],
  "remark": ""
}

// Response 201
{ "id": 1, "contract_code": "HT-2605-001", "status": "待交房", ... }
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| property_id | int(>0) | ✅ | 必须为空闲状态 |
| tenant_id_number | string(18) | ✅ | 必须存在且无活跃合同 |
| monthly_rent | int(≥0) | ✅ | 月租金（元） |
| deposit | int(≥0) | ✅ | 押金（元） |
| rent_due_day | int(1-28) | ✅ | 每月交租日 |
| residents_count | int(>0) | ❌ | 居住人数，默认1 |
| water_fee | int(≥0) | ❌ | 水费，默认30×人数 |
| start_date | date | ✅ | YYYY-MM-DD |
| end_date | date | ✅ | 必须晚于 start_date |
| key_count | int(≥0) | ❌ | 钥匙数量 |
| items | array | ❌ | 物品清单 |

**创建前置条件**：房产空闲 + 租客无活跃合同 + end_date > start_date

### GET `/api/contracts` — 合同列表

`?status=待交房|已租|退租处理中|已结算-已退租`

默认排除"已结算-已退租"状态的合同。

### GET `/api/contracts/{id}` — 合同详情

### PUT `/api/contracts/{id}` — 编辑合同

- **待交房合同**: 修改立即生效
- **已租合同**: 修改标记为待生效（`has_pending_changes=true`），下次生成账单时自动应用
- **退租处理中/已结算合同**: 不可编辑

### POST `/api/contracts/{id}/items` — 添加物品

```json
{ "item_name": "冰箱", "quantity": 1 }
```

### DELETE `/api/contracts/{id}/items/{item_id}` — 删除物品

### POST `/api/contracts/{id}/images` — 上传合同图片

`multipart/form-data`, field: `file`

### DELETE `/api/contracts/{id}/images/{image_id}` — 删除合同图片

### POST `/api/contracts/{id}/cancel` — 作废合同

⚠️ 仅"待交房"状态可作废。作废后释放房产为"空闲"。

### POST `/api/contracts/{id}/start-termination` — 发起退租

⚠️ 仅"已租"状态可发起。合同状态 → "退租处理中"。

### POST `/api/contracts/{id}/cancel-termination` — 取消退租

⚠️ 仅"退租处理中"且尚未确认结算单时可取消。已确认结算则不可取消。

---

## 域4: 验收管理 `/api/inspections`

### POST `/api/inspections/move-in` — 交房验收

```json
// Request
{
  "contract_id": 1, "inspection_date": "2026-01-01",
  "meter_base_reading": 1000,
  "key_delivery_detail": "{\"main\": 2, \"mailbox\": 1}"
}
```

⚠️ 仅"待交房"合同可验收。验收后合同→"已租"，房产→"已租"，自动从合同物品清单复制验收明细。

### GET `/api/inspections/move-in/{contract_id}` — 查看交房验收

### PUT `/api/inspections/move-in/{inspection_id}/items/{item_id}` — 更新交房物品状态

```json
{ "status": "完好|有瑕疵", "defect_remark": "轻微划痕" }
```

### POST `/api/inspections/move-in/{inspection_id}/images` — 上传验收照片

### POST `/api/inspections/move-in/{inspection_id}/signatures` — 上传签名

`?role=landlord|tenant`, multipart/form-data

### POST `/api/inspections/move-out` — 退房验收

```json
// Request
{
  "contract_id": 1, "inspection_date": "2026-05-25",
  "meter_reading": 2000, "key_return_status": "已归还",
  "key_deduction": 0, "electricity_deduction": 0
}
```

⚠️ 仅"退租处理中"合同可验收。电费扣款自动计算：`(当前读数 - 最后抄表读数或交房底数) × 1.2元/度`

### GET `/api/inspections/move-out/{contract_id}` — 查看退房验收

### PUT `/api/inspections/move-out/{inspection_id}/items/{item_id}` — 更新退房物品状态

```json
{ "status": "完好|损坏|缺失", "deduction_amount": 500 }
```

更新后自动同步未确认的结算单物品扣款。

### PUT `/api/inspections/move-out/{inspection_id}` — 编辑退房验收

修改电表读数后自动重算电费并同步结算单。

### POST `/api/inspections/move-out/{inspection_id}/images` — 上传退房照片

---

## 域5: 电表记录 `/api/meter-readings`

### POST `/api/meter-readings/readings` — 录入抄表

```json
// Request
{ "contract_id": 1, "current_reading": 1500, "reading_date": "2026-05-20", "remark": "" }

// Response 201
{ "id": 1, "record_code": "DB-0001", "consumption": 500, "electricity_amount": 600.0, ... }
```

⚠️ 每月只能抄表一次（按 reading_date 月份去重）。自动从上次抄表或交房底数取 `last_reading`。创建后自动更新当月账单电费。

### GET `/api/meter-readings/contracts/{contract_id}/readings` — 抄表列表

按 reading_date 升序，自动检测读数连续性警告。

### GET `/api/meter-readings/readings/{id}` — 抄表详情

### PUT `/api/meter-readings/readings/{id}` — 修改抄表

自动重算 consumption + electricity_amount，级联更新下一笔 last_reading 和当月账单电费。

### POST `/api/meter-readings/readings/{id}/photo` — 上传电表照片

---

## 域6: 账单管理 `/api/bills`

### POST `/api/bills/generate/{contract_id}` — 生成账单

```json
// Request
{ "bill_month": "2026-05" }

// Response 201
{ "id": 1, "bill_code": "ZD-2605-001", "total": 2560.0, "status": "未付", ... }
```

⚠️ 自动应用合同的待生效变更。月份在合同期内 + 不重复 + 不晚于未来月份时才生成。

### POST `/api/bills/auto-generate` — 自动生成所有缺失账单

无需参数，自动遍历所有活跃合同生成缺失月份的账单。

### GET `/api/bills` — 账单列表

| 参数 | 说明 |
|------|------|
| `?contract_id=` | 按合同筛选 |
| `?contract_ids=` | 按合同批量筛选（逗号分隔） |
| `?status=未付\|已付\|部分付\|逾期` | 逾期 = 未付/部分付 + due_date < 今天 |

### GET `/api/bills/{bill_id}` — 账单详情

### POST `/api/bills/{bill_id}/other-fees` — 追加其他费用

```json
{ "fee_name": "维修费", "amount": 200, "remark": "空调维修" }
```

自动更新 total 和 status。

### POST `/api/bills/{bill_id}/dunning` — 发送催收

```json
{ "sms_content": "【房东】您好，请于3月5日前缴清租金。" }
```

⚠️ 仅记录催收日志，不实际发送短信。

### GET `/api/bills/{bill_id}/payments` — 账单收款记录

---

## 域7: 收款管理 `/api/payments`

### POST `/api/payments/single` — 单笔收款

```json
// Request
{ "bill_id": 1, "amount": 2000, "payment_date": "2026-05-25", "payment_method": "微信" }

// Response 201
{ "id": 1, "total_amount": 2000, "allocations": [{ "bill_id": 1, "amount": 2000 }] }
```

⚠️ amount ≤ 账单剩余待付金额。收款后自动更新账单状态（部分付/已付）。

### POST `/api/payments/batch` — 批量收款（合并付款）

```json
// Request
{ "bill_ids": [1, 2, 3], "total_amount": 5000, "payment_date": "2026-05-25", "payment_method": "支付宝" }
```

⚠️ 至少 2 条账单。按剩余待付比例分摊，最后一条吸收余额。

### GET `/api/payments` — 收款列表

### GET `/api/payments/{id}` — 收款详情

---

## 域8: 结算管理 `/api/settlements`

### POST `/api/settlements/{contract_id}` — 生成结算单

```json
// Request
{ "other_deduction": 0, "remark": "" }

// Response 200
{
  "id": 1, "deposit_total": 2000,
  "electricity_deduction": 360.0, "item_damage_deduction": 300,
  "item_missing_deduction": 800, "key_deduction": 0,
  "unpaid_bills_total": 2800, "other_deduction": 0,
  "actual_refund": -2260.0
}
```

⚠️ 仅"退租处理中"合同 + 已完成退房验收。如已有未确认结算单则覆盖重算。自动汇总物品扣款和未付账单。

**计算公式**: `actual_refund = deposit_total - electricity_deduction - item_damage_deduction - item_missing_deduction - key_deduction - unpaid_bills_total - other_deduction`

### GET `/api/settlements/{contract_id}` — 查看结算单

### POST `/api/settlements/{contract_id}/confirm` — 确认结算

```json
// Request
{ "refund_date": "2026-05-25", "refund_method": "微信" }
```

⚠️ actual_refund 必须 ≥ 0（押金够扣）。确认后：
- 持久化 actual_refund
- 合同 → "已结算-已退租"
- 房产 → "空闲"
- 租客 → "已退租"（如无其他活跃合同）

---

## 域9: 系统功能

### GET `/api/health` — 健康检查（免认证）

```json
{ "status": "ok" }
```

### GET `/api/dashboard` — 仪表盘

```json
{
  "overdue_bill_count": 5,
  "contract_summary": [{ "status": "已租", "count": 10 }],
  "vacant_count": 3,
  "pending_rent": 25000.0,
  "pending_contract_ids": [1, 2, 3]
}
```

### GET `/api/backup` — 数据库备份

备份到 `backend/backup/landlord_YYYYMMDD.db`。

### GET `/api/backup/excel` — Excel 导出

导出全部 18 张表为 .xlsx 文件。

### POST `/api/backup/restore` — Excel 恢复

`multipart/form-data`, field: `file`

⚠️ **危险操作**：清空全部数据后导入。建议先执行 `/api/backup` 备份。

---

## 业务链流程

| 链 | 名称 | 步骤 |
|---|------|------|
| A | 新房入市出租 | 创建房产 → 创建租客 → 签合同(待交房) |
| B | 日常运营收租 | 交房验收 → 每月抄表 → 生成账单 → 收款 → 催收 |
| C | 合同变更延迟生效 | 编辑已租合同(涨租) → has_pending_changes → 下月账单自动应用新租金 |
| D | 退租清算退场 | 发起退租 → 最终抄表 → 退房验收 → 物品定损 → 未付账单 → 生成结算单 → 确认退款 → 归档 |
| E | 作废合同回滚 | 待交房合同 → 作废 → 释放房产 |
| F | 退租反悔取消 | 发起退租 → 取消退租 → 恢复已租 |
| G | 归档与清理 | 租客退租 → 5个月后自动/手动清理 |
| H | Excel备份恢复 | 导出 → 修改 → 恢复 |
