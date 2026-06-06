# 数据库设计

## 概述

- **数据库**: SQLite 3 (WAL mode)
- **ORM**: SQLAlchemy 2.x 声明式映射
- **表数量**: 18 张数据表 + 3 个触发器
- **时区**: 北京时间 UTC+8，所有时间以字符串格式 `YYYY-MM-DD HH:MM:SS` 存储

## 表结构

### 1. tenants — 租客

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id_number | TEXT | PK | 18位身份证号 |
| name | TEXT | NOT NULL | 姓名 |
| phone | TEXT | NOT NULL | 11位手机号 |
| status | TEXT | NOT NULL, DEFAULT '在用' | 在用/已退租 |
| archived_at | TEXT | NULL | 退租归档时间 |
| remark | TEXT | DEFAULT '' | 备注 |
| created_at | TEXT | NOT NULL | 创建时间 |
| updated_at | TEXT | NOT NULL | 更新时间（触发器自动维护） |

### 2. properties — 房产

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | |
| property_code | TEXT | NOT NULL UNIQUE | 自动生成 FJ-001, FJ-002... |
| name | TEXT | NOT NULL | 房产名称 |
| address | TEXT | NOT NULL | 地址 |
| status | TEXT | NOT NULL, CHECK | 空闲/已租/维修中 |
| remark | TEXT | DEFAULT '' | 备注 |
| created_at | TEXT | NOT NULL | |
| updated_at | TEXT | NOT NULL | 触发器自动维护 |

### 3. contracts — 合同

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | |
| contract_code | TEXT | NOT NULL UNIQUE | HT-YYMM-NNN |
| property_id | INTEGER | FK → properties.id | 关联房产 |
| tenant_id_number | TEXT | FK → tenants.id_number | 关联租客 |
| residents_count | INTEGER | NOT NULL, >0 | 居住人数 |
| monthly_rent | INTEGER | NOT NULL, ≥0 | 月租金（元） |
| deposit | INTEGER | NOT NULL, ≥0 | 押金（元） |
| payment_method | TEXT | NOT NULL, DEFAULT '月付' | 付款方式 |
| rent_due_day | INTEGER | NOT NULL, 1-28 | 每月交租日 |
| water_fee | INTEGER | NOT NULL, DEFAULT 0 | 水费（元/月） |
| start_date | TEXT | NOT NULL | YYYY-MM-DD |
| end_date | TEXT | NOT NULL | YYYY-MM-DD |
| key_count | INTEGER | NOT NULL, DEFAULT 0 | 钥匙数量 |
| status | TEXT | NOT NULL, CHECK | 待交房/已租/退租处理中/已结算-已退租 |
| remark | TEXT | DEFAULT '' | |
| has_pending_changes | INTEGER | NOT NULL, DEFAULT 0 | 0/1，是否有待生效变更 |
| pending_changes_json | TEXT | NULL | JSON，待生效字段变更 |
| pending_items_json | TEXT | NULL | JSON，待生效物品变更 |
| created_at | TEXT | NOT NULL | |
| updated_at | TEXT | NOT NULL | 触发器自动维护 |

**索引**: `(property_id)`, `(tenant_id_number)`, `(status)`

### 4. contract_items — 合同物品清单

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | |
| contract_id | INTEGER | FK → contracts.id CASCADE | |
| item_name | TEXT | NOT NULL | |
| quantity | INTEGER | NOT NULL, >0 | |
| sort_order | INTEGER | NOT NULL, DEFAULT 0 | |

### 5. contract_images — 合同图片

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | |
| contract_id | INTEGER | FK → contracts.id CASCADE | |
| image_path | TEXT | NOT NULL | 相对路径 |
| sort_order | INTEGER | NOT NULL, DEFAULT 0 | |

### 6. move_in_inspections — 交房验收

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | |
| contract_id | INTEGER | FK → contracts.id CASCADE, UNIQUE | 一对一 |
| inspection_date | TEXT | NOT NULL | |
| meter_base_reading | INTEGER | NOT NULL | 电表底数 |
| key_delivery_detail | TEXT | NOT NULL, DEFAULT '{}' | JSON，钥匙交付详情 |
| meter_photo_path | TEXT | NULL | 电表照片 |
| landlord_signature_path | TEXT | NULL | 房东签名 |
| tenant_signature_path | TEXT | NULL | 租客签名 |
| created_at | TEXT | NOT NULL | |

### 7. move_in_inspection_items — 交房物品明细

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | |
| inspection_id | INTEGER | FK → move_in_inspections.id CASCADE | |
| item_name | TEXT | NOT NULL | |
| quantity | INTEGER | NOT NULL | |
| status | TEXT | NOT NULL, CHECK | 完好/有瑕疵 |
| defect_remark | TEXT | DEFAULT '' | 瑕疵说明 |

### 8. move_in_inspection_images — 交房照片

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | |
| inspection_id | INTEGER | FK → move_in_inspections.id CASCADE | |
| image_path | TEXT | NOT NULL | |
| sort_order | INTEGER | NOT NULL, DEFAULT 0 | |

### 9. meter_readings — 电表记录

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | |
| record_code | TEXT | NOT NULL UNIQUE | DB-NNNN |
| contract_id | INTEGER | FK → contracts.id CASCADE | |
| last_reading | INTEGER | NULL | 上次读数 |
| current_reading | INTEGER | NOT NULL | 本次读数 |
| consumption | FLOAT | NULL | 用电量（派生） |
| electricity_amount | FLOAT | NOT NULL, DEFAULT 0 | 电费（派生） |
| reading_date | TEXT | NOT NULL | YYYY-MM-DD |
| meter_photo_path | TEXT | NULL | |
| remark | TEXT | DEFAULT '' | |
| created_at | TEXT | NOT NULL | |

**计算**: `consumption = current_reading - last_reading`, `electricity_amount = consumption × 1.2`

### 10. bills — 账单

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | |
| bill_code | TEXT | NOT NULL UNIQUE | ZD-YYMM-NNN |
| contract_id | INTEGER | FK → contracts.id CASCADE | |
| bill_month | TEXT | NOT NULL, UNIQUE(contract_id, bill_month) | YYYY-MM |
| rent | INTEGER | NOT NULL | 租金 |
| water_fee | INTEGER | NOT NULL, DEFAULT 0 | 水费 |
| electricity_fee | FLOAT | NOT NULL, DEFAULT 0 | 电费 |
| total | FLOAT | NOT NULL, DEFAULT 0 | 总额 |
| generated_date | TEXT | NOT NULL | 生成日期 |
| due_date | TEXT | NOT NULL | 截止日期 |
| status | TEXT | NOT NULL, CHECK | 未付/已付/部分付 |
| remark | TEXT | DEFAULT '' | |
| created_at | TEXT | NOT NULL | |

**索引**: `(contract_id)`, `(bill_month)`, `(status)`

### 11. bill_other_fees — 账单其他费用

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | |
| bill_id | INTEGER | FK → bills.id CASCADE, UNIQUE(bill_id, fee_name) | |
| fee_name | TEXT | NOT NULL | 费用名称 |
| amount | INTEGER | NOT NULL, ≥0 | 金额 |
| remark | TEXT | DEFAULT '' | |

### 12. payments — 收款

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | |
| payment_date | TEXT | NOT NULL | |
| total_amount | INTEGER | NOT NULL, >0 | 收款总额 |
| payment_method | TEXT | NOT NULL, CHECK | 微信/支付宝/银行转账/现金 |
| remark | TEXT | DEFAULT '' | |
| created_at | TEXT | NOT NULL | |

### 13. payment_allocations — 收款分摊

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | |
| payment_id | INTEGER | FK → payments.id CASCADE, UNIQUE(payment_id, bill_id) | |
| bill_id | INTEGER | FK → bills.id CASCADE | |
| amount | INTEGER | NOT NULL, >0 | 分摊金额 |

### 14. dunning_logs — 催收日志

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | |
| bill_id | INTEGER | FK → bills.id CASCADE | |
| dunning_time | TEXT | NOT NULL | 催收时间 |
| sms_content | TEXT | NOT NULL | 催收内容 |

### 15. move_out_inspections — 退房验收

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | |
| contract_id | INTEGER | FK → contracts.id CASCADE | |
| inspection_date | TEXT | NOT NULL | |
| meter_reading | INTEGER | NOT NULL | 电表读数 |
| electricity_deduction | FLOAT | NOT NULL, DEFAULT 0 | 电费扣款 |
| key_return_status | TEXT | NOT NULL, DEFAULT '已归还' | 已归还/未归还 |
| key_deduction | INTEGER | NOT NULL, DEFAULT 0 | 钥匙扣款 |
| remark | TEXT | DEFAULT '' | |
| created_at | TEXT | NOT NULL | |

### 16. move_out_inspection_items — 退房物品明细

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | |
| inspection_id | INTEGER | FK → move_out_inspections.id CASCADE | |
| item_name | TEXT | NOT NULL | |
| quantity | INTEGER | NOT NULL | |
| status | TEXT | NOT NULL, CHECK | 完好/损坏/缺失 |
| deduction_amount | INTEGER | NOT NULL, DEFAULT 0 | 扣款金额 |

### 17. move_out_inspection_images — 退房照片

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | |
| inspection_id | INTEGER | FK → move_out_inspections.id CASCADE | |
| image_path | TEXT | NOT NULL | |
| sort_order | INTEGER | NOT NULL, DEFAULT 0 | |

### 18. settlements — 结算单

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | |
| contract_id | INTEGER | FK → contracts.id CASCADE, UNIQUE | 一对一 |
| deposit_total | INTEGER | NOT NULL | 押金总额 |
| electricity_deduction | FLOAT | NOT NULL, DEFAULT 0 | 电费扣款 |
| item_damage_deduction | INTEGER | NOT NULL, DEFAULT 0 | 物品损坏扣款 |
| item_missing_deduction | INTEGER | NOT NULL, DEFAULT 0 | 物品缺失扣款 |
| key_deduction | INTEGER | NOT NULL, DEFAULT 0 | 钥匙扣款 |
| unpaid_bills_note | TEXT | DEFAULT '' | 未付账单说明 |
| unpaid_bills_total | INTEGER | NOT NULL, DEFAULT 0 | 未付账单合计 |
| other_deduction | INTEGER | NOT NULL, DEFAULT 0 | 其他扣款 |
| actual_refund | INTEGER | NULL | 实际退款（确认时持久化） |
| refund_date | TEXT | NULL | 退款日期 |
| refund_method | TEXT | NULL | 退款方式 |
| settled_at | TEXT | NULL | 确认时间，NULL=未确认 |
| remark | TEXT | DEFAULT '' | |
| created_at | TEXT | NOT NULL | |

## ER 关系图

```
properties ──< contracts >── tenants
                  │
     ┌────────────┼────────────┬──────────┬──────────────┐
     │            │            │          │              │
contract_items  contract_images  │    meter_readings    bills
     │            │            │          │              │
     ▼            ▼            ▼          ▼              ▼
move_in_      move_in_     move_out_   payments    bill_other_fees
inspection    inspection   inspection     │              │
  items        images        items      allocs      dunning_logs
     │                          │
     └──────────────────────────┘
                │
                ▼
          settlements
```

## 触发器

### before_update — 自动维护 updated_at

对 `contracts`, `tenants`, `properties` 三张表的每次 UPDATE 操作自动设置 `updated_at = beijing_now_str()`。

## 数据库 WAL 配置

每次连接时执行：
```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
```

## 编码规范

| 列 | 类型 | 编码格式 | 示例 |
|----|------|----------|------|
| contract_code | TEXT | `{PREFIX}-YYMM-NNN` | HT-2605-001 |
| bill_code | TEXT | `{PREFIX}-YYMM-NNN` | ZD-2605-001 |
| property_code | TEXT | `{PREFIX}-NNN` | FJ-001 |
| record_code | TEXT | `{PREFIX}-NNNN` | DB-0001 |
| 所有日期 | TEXT | `YYYY-MM-DD` | 2026-05-20 |
| 所有时间 | TEXT | `YYYY-MM-DD HH:MM:SS` | 2026-05-20 14:30:00 |

## 数据生命周期

```
创建 → 活跃使用 → 退租结算 → 归档(5个月) → 自动清理
```

- 结算后的合同保留在数据库中标记为"已结算-已退租"
- 退租租客的合同数据在租客档案中永久可查
- 归档超过 5 个月的租客由 `/api/tenants/cleanup` 物理删除
