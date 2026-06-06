"""Phase 1 API verification — test all endpoints via httpx."""
import json, sys
sys.path.insert(0, "..")
from httpx import Client, HTTPStatusError

BASE = "http://127.0.0.1:8000"
c = Client(base_url=BASE, timeout=10)

def ok(r):
    """Check response is 2xx."""
    try:
        r.raise_for_status()
    except HTTPStatusError as e:
        print(f"  FAIL: HTTP {r.status_code} — {r.text[:200]}")
        return False
    return True

def show(r, label=""):
    if ok(r):
        try:
            print(f"  {label}: {json.dumps(r.json(), ensure_ascii=False, indent=2)[:300]}")
        except Exception:
            print(f"  {label}: {r.text[:200]}")
    return r

def test(name, method, path, body=None, expect_status=200):
    print(f"\n--- {name} ---")
    try:
        r = c.request(method, path, json=body)
        if r.status_code != expect_status:
            print(f"  WARN: expected {expect_status}, got {r.status_code}")
            print(f"  body: {r.text[:300]}")
            return r
        show(r, f"{method} {path}")
        return r
    except Exception as e:
        print(f"  ERROR: {e}")
        return None

print("=" * 60)
print("PHASE 1 API VERIFICATION")
print("=" * 60)

# 1. Health & Dashboard
test("Health", "GET", "/api/health")
test("Dashboard", "GET", "/api/dashboard")

# 2. Properties CRUD
print("\n\n### PROPERTIES ###")

# Clean up any existing test data for property 99
try:
    c.delete("/api/properties/99")
except Exception:
    pass

test("List properties", "GET", "/api/properties")
test("Filter by status", "GET", "/api/properties?status=空闲")
test("Create property", "POST", "/api/properties", {
    "name": "锦绣花园3栋502", "address": "深圳市南山区科技园路88号", "status": "空闲", "remark": "精装修"
}, 201)
test("Get property 404", "GET", "/api/properties/9999", expect_status=404)
test("Invalid status", "POST", "/api/properties", {
    "name": "Bad", "address": "X", "status": "INVALID"
}, expect_status=422)
test("Missing name", "POST", "/api/properties", {
    "address": "X", "status": "空闲"
}, expect_status=422)
test("Update property", "PUT", "/api/properties/2", {
    "name": "测试房源-已修改", "status": "维修中"
})
test("Delete property with contract", "DELETE", "/api/properties/1", expect_status=400)

# 3. Tenants CRUD
print("\n\n### TENANTS ###")

# Clean up
try:
    c.delete("/api/tenants/TEST999")
except Exception:
    pass

test("List tenants", "GET", "/api/tenants")
test("Create tenant", "POST", "/api/tenants", {
    "id_number": "TEST999", "name": "李四", "phone": "13900139000", "remark": "测试"
}, 201)
test("Duplicate tenant", "POST", "/api/tenants", {
    "id_number": "TEST999", "name": "Duplicate", "phone": "13900139000"
}, expect_status=400)
test("Get tenant", "GET", "/api/tenants/TEST999")
test("Update tenant", "PUT", "/api/tenants/TEST999", {
    "name": "李四-改", "phone": "13800138001"
})
test("Credit report", "GET", "/api/tenants/TEST999/credit")
test("Get tenant 404", "GET", "/api/tenants/NONEXIST", expect_status=404)
test("Missing name", "POST", "/api/tenants", {
    "id_number": "BAD001", "phone": "13900000000"
}, expect_status=422)

# 4. Contracts CRUD
print("\n\n### CONTRACTS ###")

# First create a free property for contract testing
r = c.post("/api/properties", json={"name": "合同测试房源", "address": "广州市天河区", "status": "空闲"})
if r.status_code == 201:
    free_prop_id = r.json()["id"]
    print(f"  Created free property id={free_prop_id}")
else:
    # Find existing free property
    r = c.get("/api/properties?status=空闲")
    props = r.json()
    free_prop_id = props[0]["id"] if props else 1
    print(f"  Using existing property id={free_prop_id}")

test("List contracts", "GET", "/api/contracts")
test("Filter by status", "GET", "/api/contracts?status=待交房")
test("Create contract", "POST", "/api/contracts", {
    "property_id": free_prop_id,
    "tenant_id_number": "TEST999",
    "residents_count": 2,
    "monthly_rent": 3000,
    "deposit": 6000,
    "rent_due_day": 5,
    "water_fee": 120,
    "start_date": "2026-06-01",
    "end_date": "2027-05-31",
    "key_count": 2,
    "items": [{"item_name": "沙发", "quantity": 1}, {"item_name": "床", "quantity": 2}],
    "remark": "测试合同"
}, 201)

# Get the contract ID
r = c.get("/api/contracts")
contracts = r.json()
contract_id = contracts[0]["id"] if contracts else None
print(f"  Contract ID: {contract_id}")

if contract_id:
    test("Get contract detail", "GET", f"/api/contracts/{contract_id}")
    test("Add item", "POST", f"/api/contracts/{contract_id}/items", {
        "item_name": "电视", "quantity": 1
    })
    test("Update contract", "PUT", f"/api/contracts/{contract_id}", {
        "monthly_rent": 3200, "remark": "调价后"
    })
    test("Create contract - property not free", "POST", "/api/contracts", {
        "property_id": free_prop_id,
        "tenant_id_number": "TEST999",
        "residents_count": 1,
        "monthly_rent": 2000,
        "deposit": 4000,
        "rent_due_day": 1,
        "start_date": "2026-06-01",
        "end_date": "2027-05-31"
    }, expect_status=400)
    test("Create contract - bad tenant", "POST", "/api/contracts", {
        "property_id": 9999,
        "tenant_id_number": "NORENT",
        "residents_count": 1,
        "monthly_rent": 2000,
        "deposit": 4000,
        "rent_due_day": 1,
        "start_date": "2026-06-01",
        "end_date": "2027-05-31"
    }, expect_status=400)
    # Lifecycle tests
    test("Cancel contract (should work: 待交房)", "POST", f"/api/contracts/{contract_id}/cancel")
    test("Cancel already cancelled (should fail)", "POST", f"/api/contracts/{contract_id}/cancel", expect_status=400)
    # Get contract status
    r = c.get(f"/api/contracts/{contract_id}")
    print(f"  Contract status after cancel: {r.json().get('status')}")

    # Delete tenant with contract (should fail)
    test("Delete tenant with contract", "DELETE", "/api/tenants/TEST999", expect_status=400)

# 5. Unexpected methods
print("\n\n### EDGE CASES ###")
test("GET on POST-only endpoint (health)", "GET", "/api/properties", expect_status=200)  # GET is valid
test("Wrong content type", "POST", "/api/properties", None, expect_status=422)  # No body
test("Empty body create", "POST", "/api/properties", {}, expect_status=422)

# Clean up
test("Delete test tenant (should fail if contract exists)", "DELETE", "/api/tenants/TEST999", expect_status=400)

print("\n\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
