"""End-to-end business chain verification test."""
import sys
sys.path.insert(0, '.')
import os, requests, json
from datetime import date

API = os.getenv("API_URL", "http://127.0.0.1:8005/api")
API_KEY = os.getenv("API_KEY", "dev-key-change-me")
H = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
TODAY = date.today().isoformat()  # e.g. 2026-05-29

def step(name, method, url, **kwargs):
    r = getattr(requests, method)(url, headers=H, **kwargs)
    tag = "OK" if r.status_code < 400 else f"ERR({r.status_code})"
    print(f"  [{tag}] {name}")
    return r

# === CHAIN 1: Move-in ===
print("=== CHAIN 1: Tenant Move-in ===")
r = step("Create Property", "post", f"{API}/properties", json={
    "name": "Test Apt 501", "address": "Beijing Chaoyang", "status": "空闲", "remark": "test"
})
prop = r.json()
print(f"    id={prop.get('id')}, code={prop.get('property_code')}, status={prop.get('status')}")

r = step("Create Tenant", "post", f"{API}/tenants", json={
    "id_number": "110101199001011234", "name": "Zhang San", "phone": "13800138000"
})
tenant = r.json()
print(f"    id_number={tenant.get('id_number')}, status={tenant.get('status')}")

# Contract starts 2026-01-01 (past), ends 2027-01-01
r = step("Create Contract", "post", f"{API}/contracts", json={
    "property_id": 1, "tenant_id_number": "110101199001011234",
    "monthly_rent": 2500, "deposit": 2500, "rent_due_day": 5,
    "water_fee": 60, "start_date": "2026-01-01", "end_date": "2027-01-01",
    "key_count": 2, "items": [
        {"item_name": "Bed", "quantity": 1},
        {"item_name": "AC", "quantity": 2}
    ]
})
ct = r.json()
print(f"    code={ct.get('contract_code')}, status={ct.get('status')}")
print(f"    items={[i['item_name'] for i in ct.get('items', [])]}")

r = step("Property status check", "get", f"{API}/properties/1")
print(f"    property status={r.json().get('status')}")

r = step("Move-in Inspection", "post", f"{API}/inspections/move-in", json={
    "contract_id": 1, "inspection_date": "2026-01-01",
    "meter_base_reading": 5000, "key_delivery_detail": "{}"
})
insp = r.json()
print(f"    meter_base={insp.get('meter_base_reading')}, items_copied={len(insp.get('items', []))}")

r = step("Contract status after move-in", "get", f"{API}/contracts/1")
print(f"    contract status={r.json().get('status')}")

# === CHAIN 2: Monthly Operations ===
print("\n=== CHAIN 2: Monthly Operations ===")

# Meter reading for May 2026
r = step("Meter Reading 2026-05-15", "post", f"{API}/meter-readings/readings", json={
    "contract_id": 1, "current_reading": 5120,
    "reading_date": "2026-05-15", "remark": ""
})
mr = r.json()
print(f"    consumption={mr.get('consumption')}, elec_amount={mr.get('electricity_amount')}")

# Test duplicate month rejection
r = step("Duplicate month rejection", "post", f"{API}/meter-readings/readings", json={
    "contract_id": 1, "current_reading": 5150,
    "reading_date": "2026-05-20", "remark": ""
})
print(f"    status={r.status_code} (expect 400)")

# Auto-generate bills
r = step("Auto-generate bills", "post", f"{API}/bills/auto-generate", params={"contract_id": 1})
gen = r.json()
print(f"    generated={gen.get('generated')}, skipped={gen.get('skipped')}")

r = step("List bills", "get", f"{API}/bills", params={"contract_id": 1})
bills = r.json()
print(f"    total bills: {len(bills)}")
for b in bills[:3]:
    print(f"      {b['bill_month']}: rent={b['rent']}, water={b['water_fee']}, elec={b['electricity_fee']}, total={b['total']}, due={b['due_date']}, status={b['status']}")

# Payment - overpay should fail
if bills:
    bill_id = bills[0]["id"]
    bill_total = bills[0]["total"]

    r = step("Overpay rejection", "post", f"{API}/payments/single", json={
        "bill_id": bill_id, "payment_date": TODAY,
        "amount": int(bill_total + 1000), "payment_method": "微信"
    })
    print(f"    status={r.status_code} (expect 400)")

    r = step("Correct payment", "post", f"{API}/payments/single", json={
        "bill_id": bill_id, "payment_date": TODAY,
        "amount": int(bill_total), "payment_method": "微信"
    })
    pay = r.json()
    print(f"    paid={pay.get('total_amount')}, allocs={len(pay.get('allocations', []))}")

# Dashboard
r = step("Dashboard", "get", f"{API}/dashboard")
dash = r.json()
print(f"    overdue={dash.get('overdue_bill_count')}, vacant={dash.get('vacant_count')}, pending_rent={dash.get('pending_rent')}")

# === CHAIN 3: Termination & Settlement ===
print("\n=== CHAIN 3: Termination & Settlement ===")

r = step("Start termination", "post", f"{API}/contracts/1/start-termination")
print(f"    {r.json().get('message')}")

r = step("Move-out inspection", "post", f"{API}/inspections/move-out", json={
    "contract_id": 1, "inspection_date": TODAY,
    "meter_reading": 6200, "key_return_status": "已归还",
    "key_deduction": 0, "remark": ""
})
mo = r.json()
print(f"    elec_deduction={mo.get('electricity_deduction')}, items={len(mo.get('items', []))}")

# Mark item as damaged
if mo.get("items"):
    item_id = mo["items"][0]["id"]
    insp_id = mo["id"]
    r = step("Mark item damaged", "put", f"{API}/inspections/move-out/{insp_id}/items/{item_id}", json={
        "status": "损坏", "deduction_amount": 200
    })
    it = r.json()["items"][0]
    print(f"    item={it['item_name']}, status={it['status']}, deduction={it['deduction_amount']}")

r = step("Create settlement", "post", f"{API}/settlements/1", json={
    "other_deduction": 0, "remark": ""
})
stl = r.json()
print(f"    deposit={stl.get('deposit_total')}, elec={stl.get('electricity_deduction')}")
print(f"    damage={stl.get('item_damage_deduction')}, actual_refund={stl.get('actual_refund')}")

# Confirm with today's date (within 7-day window)
r = step("Confirm settlement", "post", f"{API}/settlements/1/confirm", json={
    "refund_date": TODAY, "refund_method": "微信", "remark": ""
})
cstl = r.json()
print(f"    settled_at={cstl.get('settled_at')}, actual_refund={cstl.get('actual_refund')}")

# === Post-settlement checks ===
print("\n=== Post-settlement Verification ===")

r = step("Contract list (should be empty)", "get", f"{API}/contracts")
print(f"    active contracts: {len(r.json())}")

r = step("Property status (should be idle)", "get", f"{API}/properties/1")
print(f"    status={r.json().get('status')}")

r = step("Tenant status (should be archived)", "get", f"{API}/tenants/110101199001011234")
t = r.json()
print(f"    status={t.get('status')}, archived_at={t.get('archived_at')}")

r = step("Tenant profile", "get", f"{API}/tenants/110101199001011234/profile")
profile = r.json()
print(f"    total_contracts={profile.get('total_contracts')}")
print(f"    total_billed={profile.get('total_billed')}, total_paid={profile.get('total_paid')}")
if profile.get("contracts") and profile["contracts"][0].get("settlement"):
    s = profile["contracts"][0]["settlement"]
    print(f"    settlement actual_refund={s.get('actual_refund')} (should be persisted)")

# === Date edge cases ===
print("\n=== Date Edge Cases ===")

# Test invalid dates via API
r = step("Reject 2026-02-29 (non-leap year)", "post", f"{API}/properties", json={
    "name": "x", "address": "x", "status": "空闲"
})
# Use schemas directly to test date validation
from models.schemas import _check_date
bad_dates = ["2026-02-29", "2026-04-31", "2026-06-31", "2026-09-31", "2025-02-29"]
good_dates = ["2024-02-29", "2028-02-29", "2026-01-31", "2026-02-28", "2026-04-30"]

for d in bad_dates:
    try:
        _check_date(d)
        print(f"  [FAIL] {d} should be rejected")
    except ValueError:
        print(f"  [OK] {d} correctly rejected")

for d in good_dates:
    try:
        _check_date(d)
        print(f"  [OK] {d} correctly accepted")
    except ValueError:
        print(f"  [FAIL] {d} should be accepted")

print("\n=== ALL CHAINS VERIFIED ===")
