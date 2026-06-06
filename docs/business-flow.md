# 业务流程

## 状态机

### 合同状态流转

```
                      ┌─────────────────────┐
                      │       待交房         │
                      └──────────┬──────────┘
                                 │ 交房验收
                                 ▼
                      ┌─────────────────────┐
              ┌────── │        已租          │
              │       └──────────┬──────────┘
              │ 取消退租          │ 发起退租
              │                  ▼
              │       ┌─────────────────────┐
              └──────→│     退租处理中       │
                      └──────────┬──────────┘
                                 │ 确认结算
                                 ▼
                      ┌─────────────────────┐
                      │   已结算-已退租      │
                      └─────────────────────┘

待交房 → 作废 → (合同物理删除，房产释放)
```

### 租客状态流转

```
      在 用 ──────→ 已退租 ──────→ (5个月后清理)
        ↑              │
        └─── 恢复 ─────┘
```

### 房产状态流转

```
      空闲 ──→ 已租 ──→ 空闲 (结算确认后自动释放)
        │                ↑
        └── 维修中 ──────┘
```

### 账单状态流转

```
      未付 ──→ 部分付 ──→ 已付
        │         │         ↑
        └─────────┴─────────┘
            (收款分摊自动更新)
```

---

## 业务链 A: 新房入市出租

```
1. 创建房产 (status=空闲)
2. 创建租客 (status=在用)
3. 签约 → contract status=待交房, property status=已租
4. (续: 交房验收 → 进入日常运营)
```

**约束**: 房产必须空闲 + 租客必须无活跃合同 + 合同结束日期 > 开始日期

---

## 业务链 B: 日常运营收租

```
月循环:
  1. 抄表 (每月一次) → 自动更新当月账单电费
  2. 生成账单 (每月一次) → rent + water_fee + electricity_fee = total
  3. 收款 → 单笔或批量 → 更新账单状态 (部分付/已付)
  4. [可选] 催收 → 记录催收日志
  5. [可选] 追加其他费用 → 更新 total
```

**抄表逻辑**:
- `last_reading` = 上次抄表的 `current_reading` 或交房验收的 `meter_base_reading`
- `consumption` = `current_reading - last_reading`
- `electricity_fee` = `consumption × 1.2 元/度`

**账单生成逻辑**:
- 月份必须在 [start_date, end_date] ∩ [start_date, 当月] 内
- due_date = 当月 rent_due_day，如已过则为生成日+7天
- 自动应用合同待生效变更

---

## 业务链 C: 合同变更延迟生效

```
已租合同修改租金等核心字段 →
  ├─ 当前值不变
  ├─ has_pending_changes = 1
  └─ pending_changes_json 存储变更内容

下次生成账单时 →
  ├─ _apply_pending_changes() 应用所有待生效变更
  ├─ has_pending_changes = 0
  └─ 新账单使用新租金
```

**延迟生效字段**: monthly_rent, deposit, rent_due_day, water_fee, residents_count, key_count, start_date, end_date, remark, items

---

## 业务链 D: 租客退租清算退场

```
1. 发起退租 → contract status = 退租处理中
2. 最终抄表 (可选，用于计算退房电费)
3. 退房验收 →
   ├─ 读取最后抄表或交房底数
   ├─ 电费扣款 = (meter_reading - 基准) × 1.2
   ├─ 钥匙交回状态 + 扣款
   └─ 物品状态定损 (完好/损坏/缺失 + deduction_amount)
4. 生成未付月份账单
5. 生成结算单 →
   ├─ 汇总: 电费 + 物品损坏 + 物品缺失 + 钥匙 + 未付账单 + 其他
   └─ actual_refund = deposit_total - Σ deductions
6. 确认结算 (actual_refund ≥ 0) →
   ├─ 持久化 actual_refund
   ├─ contract → 已结算-已退租
   ├─ property → 空闲
   └─ tenant → 已退租 (如无其他活跃合同)
7. 5个月后 → 自动清理归档数据
```

---

## 业务链 E: 作废合同回滚

```
待交房合同 →
  作废 → 物理删除合同 + 释放房产(status=空闲)
```

**限制**: 仅"待交房"可作废。已租/退租处理中必须走退租流程。

---

## 业务链 F: 退租反悔取消

```
已租 → 发起退租 → 退租处理中 →
  取消退租 →
    ├─ contract → 已租
    ├─ 删除退房验收记录 (如有)
    └─ 删除未确认的结算单 (如有)
```

**限制**: 结算单已确认后不可取消。

---

## 业务链 G: 数据归档与清理

```
退租确认 →
  ├─ 租客 status = 已退租, archived_at = now
  └─ 合同保留在归档可查列表中

GET /api/tenants/archived?q=   → 查询归档5个月内的租客
POST /api/tenants/cleanup      → 物理删除归档超5个月的租客及关联数据
```

**清理范围**: 租客 → 合同(CASCADE) → 账单 → 收款分摊(仅清理孤儿 Payment) → 抄表 → 验收记录

---

## 业务链 H: 数据备份恢复

```
导出: GET /api/backup/excel → 18张表 → .xlsx 文件
备份: GET /api/backup → landlord_YYYYMMDD.db

恢复: POST /api/backup/restore (upload .xlsx) →
  ├─ DROP ALL TABLES (逆序: 子表→主表)
  ├─ IMPORT 18 sheets
  └─ COMMIT
```

⚠️ 恢复为全量替换，当前数据将丢失。
