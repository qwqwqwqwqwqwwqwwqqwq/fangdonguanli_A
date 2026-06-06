# -*- coding: utf-8 -*-
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import httpx

BASE = "http://localhost:8002/api"
API_KEY = "dev-key-change-me"
HEADERS = {"X-API-Key": API_KEY}
passed = 0
failed = 0

def test(name, fn):
    global passed, failed
    try:
        result = fn()
        if result:
            passed += 1
            print(f"  [PASS] {name}")
        else:
            failed += 1
            print(f"  [FAIL] {name}")
    except httpx.HTTPStatusError as e:
        failed += 1
        print(f"  [FAIL] {name}: HTTP {e.response.status_code} {e.response.text[:100]}")
    except Exception as e:
        failed += 1
        print(f"  [FAIL] {name}: {e}")

def api(method, path, **kw):
    kw.setdefault("headers", {}).update(HEADERS)
    r = httpx.request(method, f"{BASE}{path}", **kw)
    r.raise_for_status()
    return r.json()

print("=== Setup ===")

import time
ts = str(int(time.time()))[-6:]

prop = api("POST", "/properties", json={
    "name": f"E2E test apt {ts}", "address": "Beijing E2E test road", "area": 80.0,
    "rooms": 2, "halls": 1, "rent": 3500.0, "deposit": 3500.0,
    "floor": 5, "orientation": "south", "decoration": "fine",
    "property_type": "residential", "status": "空闲"
})
prop_id = prop["id"]
test("Create property", lambda: prop_id > 0)

tenant_id = f"1101011990{ts}"[:18]

api("POST", "/tenants", json={
    "name": "E2E Test Tenant", "id_number": tenant_id,
    "phone": "13900001111",
})

contract = api("POST", "/contracts", json={
    "property_id": prop_id, "tenant_id_number": tenant_id,
    "start_date": "2026-05-01", "end_date": "2027-04-30",
    "monthly_rent": 3500.0, "deposit": 3500.0,
    "rent_due_day": 5, "water_fee": 60.0,
    "residents_count": 2,
    "items": [
        {"item_name": "TV", "quantity": 1, "sort_order": 1},
        {"item_name": "Fridge", "quantity": 1, "sort_order": 2},
        {"item_name": "Washer", "quantity": 1, "sort_order": 3},
    ]
})
cid = contract["id"]
test("Create contract", lambda: contract["status"] == "待交房")
print(f"  contract_id={cid}, property_id={prop_id}")

print("\n=== Move-in Inspection ===")

insp = api("POST", "/inspections/move-in", json={
    "contract_id": cid, "inspection_date": "2026-05-01",
    "meter_base_reading": 1000.0,
    "key_delivery_detail": "2 main door keys, 1 room key"
})
insp_id = insp["id"]
test("Create move-in inspection", lambda: insp_id > 0)

insp_get = api("GET", f"/inspections/move-in/{cid}")
test("Get move-in inspection", lambda: insp_get["id"] == insp_id)
test("Items copied from contract", lambda: len(insp_get["items"]) == 3)
test("Items default OK", lambda: all(i["status"] == "完好" for i in insp_get["items"]))

item_id = insp_get["items"][0]["id"]
api("PUT", f"/inspections/move-in/{insp_id}/items/{item_id}", json={
    "status": "有瑕疵", "defect_remark": "TV screen scratch"
})
insp_upd = api("GET", f"/inspections/move-in/{cid}")
test("Update item status", lambda: insp_upd["items"][0]["status"] == "有瑕疵")

c = api("GET", f"/contracts/{cid}")
test("Contract status -> 已租", lambda: c["status"] == "已租")
p = api("GET", f"/properties/{prop_id}")
test("Property status -> 已租", lambda: p["status"] == "已租")

print("\n=== Meter Readings ===")

r1 = api("POST", "/meter-readings/readings", json={
    "contract_id": cid, "reading_month": "2026-05",
    "current_reading": 1100.0, "electricity_amount": 80.0,
    "reading_date": "2026-05-31", "remark": ""
})
test("Create reading 2026-05", lambda: r1["id"] > 0)

r2 = api("POST", "/meter-readings/readings", json={
    "contract_id": cid, "reading_month": "2026-06",
    "current_reading": 1200.0, "electricity_amount": 80.0,
    "reading_date": "2026-06-30", "remark": ""
})
test("Create reading 2026-06", lambda: r2["id"] > 0)

readings = api("GET", f"/meter-readings/contracts/{cid}/readings")
test("List readings", lambda: len(readings) >= 2)
test("No continuity warnings", lambda: all(r.get("warning") is None for r in readings))

r3 = api("PUT", f"/meter-readings/readings/{r1['id']}", json={"electricity_amount": 85.0})
test("Update reading", lambda: r3["electricity_amount"] == 85.0)

print("\n=== Bills ===")

b1 = api("POST", f"/bills/generate/{cid}", json={"bill_month": "2026-05"})
test("Generate bill 2026-05", lambda: b1["id"] > 0)
test("Bill rent correct", lambda: b1["rent"] == 3500.0)
test("Bill water_fee correct", lambda: b1["water_fee"] == 60.0)
test("Bill status unpaid", lambda: b1["status"] == "未付")

r = httpx.post(f"{BASE}/bills/generate/{cid}", json={"bill_month": "2026-05"}, headers=HEADERS)
test("Dupe bill rejected", lambda: r.status_code == 400)

b2 = api("POST", f"/bills/generate/{cid}", json={"bill_month": "2026-06"})
test("Generate bill 2026-06", lambda: b2["id"] > 0)

bills = api("GET", "/bills", params={"contract_id": cid})
test("List bills by contract", lambda: len(bills) == 2)

b1d = api("GET", f"/bills/{b1['id']}")
test("Get bill detail", lambda: b1d["bill_code"] == b1["bill_code"])

fee = api("POST", f"/bills/{b1['id']}/other-fees", json={
    "fee_name": "property fee", "amount": 100.0, "remark": "May"
})
test("Add other fee", lambda: len(fee["other_fees"]) == 1)

# Filter bills
unpaid = api("GET", "/bills", params={"status": "未付"})
test("Filter unpaid bills", lambda: all(b["status"] == "未付" for b in unpaid))

# Dunning
d1 = httpx.post(f"{BASE}/bills/{b1['id']}/dunning", json={"sms_content": "please pay"}, headers=HEADERS)
test("Dunning allowed for unpaid", lambda: d1.status_code == 200)

print("\n=== Payments ===")

p1 = api("POST", "/payments/single", json={
    "bill_id": b1["id"], "amount": 3745.0,
    "payment_date": "2026-05-10",
    "payment_method": "微信", "remark": ""
})
test("Create payment", lambda: p1["id"] > 0)

b1c = api("GET", f"/bills/{b1['id']}")
test("Bill -> paid", lambda: b1c["status"] == "已付")

d2 = httpx.post(f"{BASE}/bills/{b1['id']}/dunning", json={"sms_content": "pay"}, headers=HEADERS)
test("Dunning rejected for paid", lambda: d2.status_code == 400)

test("List payments", lambda: len(api("GET", "/payments")) >= 1)

pd = api("GET", f"/payments/{p1['id']}")
test("Get payment detail", lambda: len(pd["allocations"]) >= 1)

# Batch: < 2 bills rejected
try:
    api("POST", "/payments/batch", json={
        "bill_ids": [b2["id"]], "total_amount": 3640.0,
        "payment_date": "2026-06-10", "payment_method": "alipay", "remark": ""
    })
    test("Batch rejection for 1 bill", lambda: False)
except httpx.HTTPStatusError:
    test("Batch rejection for 1 bill", lambda: True)

# Partial payment
api("POST", "/payments/single", json={
    "bill_id": b2["id"], "amount": 2000.0,
    "payment_date": "2026-06-10", "payment_method": "支付宝", "remark": ""
})
b2c = api("GET", f"/bills/{b2['id']}")
test("Partial payment -> 部分付", lambda: b2c["status"] == "部分付")

# Pay off remaining balance so settlement can proceed
remaining = b2c["total"] - 2000
api("POST", "/payments/single", json={
    "bill_id": b2["id"], "amount": remaining,
    "payment_date": "2026-06-15", "payment_method": "支付宝", "remark": "payoff"
})
b2c2 = api("GET", f"/bills/{b2['id']}")
test("Full payment -> 已付", lambda: b2c2["status"] == "已付")

print("\n=== Move-out + Settlement ===")

api("POST", f"/contracts/{cid}/start-termination")
test("Start termination", lambda: api("GET", f"/contracts/{cid}")["status"] == "退租处理中")

mo = api("POST", "/inspections/move-out", json={
    "contract_id": cid, "inspection_date": "2026-07-01",
    "meter_reading": 1250.0, "electricity_deduction": 200.0,
    "key_return_status": "complete", "key_deduction": 0.0,
    "remark": ""
})
mo_id = mo["id"]
test("Create move-out inspection", lambda: mo_id > 0)

mo_get = api("GET", f"/inspections/move-out/{cid}")
test("Get move-out inspection", lambda: mo_get["id"] == mo_id)
test("Move-out items copied", lambda: len(mo_get["items"]) == 3)

mo_item_id = mo_get["items"][0]["id"]
api("PUT", f"/inspections/move-out/{mo_id}/items/{mo_item_id}", json={
    "status": "损坏", "deduction_amount": 200.0
})
mo_upd = api("GET", f"/inspections/move-out/{cid}")
test("Update damage deduction", lambda: mo_upd["items"][0]["status"] == "损坏")

sett = api("POST", f"/settlements/{cid}", json={
    "other_deduction": 0, "remark": ""
})
test("Create settlement", lambda: sett["id"] > 0)
test("Deposit total", lambda: sett["deposit_total"] == 3500.0)
test("Electricity deduction", lambda: sett["electricity_deduction"] == 200.0)
test("Item damage deduction", lambda: sett["item_damage_deduction"] == 200.0)
test("Actual refund 3500-200-200", lambda: sett["actual_refund"] == 3100.0)

# Dupe
r = httpx.post(f"{BASE}/settlements/{cid}", json={"other_deduction": 0}, headers=HEADERS)
test("Dupe settlement rejected", lambda: r.status_code == 400)

conf = api("POST", f"/settlements/{cid}/confirm", json={
    "refund_date": "2026-06-15",
    "refund_method": "bank transfer",
    "remark": "refunded to ICBC"
})
test("Confirm settlement", lambda: conf["refund_date"] is not None)

test("Contract -> settled", lambda: api("GET", f"/contracts/{cid}")["status"] == "已结算-已退租")
test("Property -> vacant", lambda: api("GET", f"/properties/{prop_id}")["status"] == "空闲")

print(f"\n{'='*50}")
print(f"RESULTS: {passed} PASSED, {failed} FAILED, {passed+failed} TOTAL")
if failed == 0:
    print("ALL TESTS PASSED!")
print(f"{'='*50}")
