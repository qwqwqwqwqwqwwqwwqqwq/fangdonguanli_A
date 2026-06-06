import requests, random, string, sys, json, datetime
sys.stdout.reconfigure(encoding="utf-8")
B = "http://localhost:8005/api"
H = {"X-API-Key": "dev-key-change-me"}
R = []
def ok(r): return r.status_code in (200, 201)
def ri(): return "990" + "".join(random.choice(string.digits) for _ in range(15))
def rp(): return "138" + "".join(random.choice(string.digits) for _ in range(8))
P = F = 0
def t(n,c,d=""):
    global P,F
    if c: P+=1; print(f"  PASS {n}")
    else: F+=1; print(f"  FAIL {n}: {d}")

print("=== AUDIT: 2 Samples ===")

# SAMPLE 1
print()
print("--- Sample 1: Normal ---")
s1 = "S1" + "".join(random.choice(string.digits) for _ in range(4))
r = requests.post(B+"/properties", headers=H, json={"name":f"S1P-{s1}","address":"x","status":"空闲"})
assert ok(r); pid1 = r.json()["id"]; IDLE = r.json()["status"]
r = requests.post(B+"/tenants", headers=H, json={"id_number":ri(),"name":f"Z-{s1}","phone":rp()})
assert ok(r); tid1 = r.json()["id_number"]; ACTIVE = r.json()["status"]
r = requests.post(B+"/contracts", headers=H, json={"property_id":pid1,"tenant_id_number":tid1,"monthly_rent":2500,"deposit":3000,"rent_due_day":5,"residents_count":2,"water_fee":60,"start_date":"2026-01-01","end_date":"2026-06-30","items":[{"item_name":"AC","quantity":2},{"item_name":"Bed","quantity":1},{"item_name":"Fridge","quantity":1}]})
assert ok(r); cid1 = r.json()["id"]; cc1 = r.json()["contract_code"]
print(f"Contract: {cc1} (ID={cid1})")

requests.post(B+"/inspections/move-in", headers=H, json={"contract_id":cid1,"inspection_date":"2026-01-01","meter_base_reading":500})
for dt,rd in [("2026-01-25",800),("2026-02-22",1100),("2026-03-25",1450),("2026-04-26",1800)]:
    requests.post(B+"/meter-readings/readings", headers=H, json={"contract_id":cid1,"current_reading":rd,"reading_date":dt})
bids1 = []
for m in ["2026-01","2026-02","2026-03","2026-04"]:
    r = requests.post(B+f"/bills/generate/{cid1}", headers=H, json={"bill_month":m})
    bids1.append(r.json()["id"])
for i, (bid, amt) in enumerate([(bids1[0],2860),(bids1[1],2980),(bids1[2],2000)]):
    requests.post(B+"/payments/single", headers=H, json={"bill_id":bid,"payment_date":f"2026-0{i+1}-27","amount":amt,"payment_method":"微信"})

pre1_p = requests.get(B+f"/tenants/{tid1}/profile", headers=H).json()
pre1_m = len(requests.get(B+f"/meter-readings/contracts/{cid1}/readings", headers=H).json())
pre1_b = len(requests.get(B+"/bills", headers=H, params={"contract_id":cid1}).json())
print(f"PRE: total_billed={pre1_p["total_billed"]} total_paid={pre1_p["total_paid"]} meters={pre1_m} bills={pre1_b}")

requests.post(B+f"/contracts/{cid1}/start-termination", headers=H)
r = requests.post(B+"/inspections/move-out", headers=H, json={"contract_id":cid1,"inspection_date":"2026-05-01","meter_reading":1800,"key_return_status":"已归还","key_deduction":0})
insp1 = r.json() if r.status_code in (200,201) else {}
if insp1:
    for item in insp1.get("items",[]):
        st = "损坏" if item["item_name"]=="Fridge" else "完好"
        da = 300 if item["item_name"]=="Fridge" else 0
        requests.put(B+f"/inspections/move-out/{insp1["id"]}/items/{item["id"]}", headers=H, json={"status":st,"deduction_amount":da})
r = requests.post(B+f"/settlements/{cid1}", headers=H, json={"other_deduction":0})
assert r.status_code==200; stl1 = r.json()
r = requests.post(B+f"/settlements/{cid1}/confirm", headers=H, json={"refund_date":"2026-05-15","refund_method":"银行转账"})
assert r.status_code==200
print(f"Settlement: refund={stl1["actual_refund"]}")

post1_p = requests.get(B+f"/tenants/{tid1}/profile", headers=H).json()
post1_m = len(requests.get(B+f"/meter-readings/contracts/{cid1}/readings", headers=H).json())
post1_b = len(requests.get(B+"/bills", headers=H, params={"contract_id":cid1}).json())
ct1 = requests.get(B+f"/contracts/{cid1}", headers=H).json()
print(f"POST: total_billed={post1_p["total_billed"]} total_paid={post1_p["total_paid"]} meters={post1_m} bills={post1_b}")

t("Tenant archived",requests.get(B+f"/tenants/{tid1}",headers=H).json()["status"]=="已退租")
t("Contract settled","已结算" in ct1["status"])
t("Property freed",requests.get(B+f"/properties/{pid1}",headers=H).json()["status"]==IDLE)
t("Bills preserved",pre1_b==post1_b)
t("Meters preserved",pre1_m==post1_m)
t("Total billed same",pre1_p["total_billed"]==post1_p["total_billed"])
t("Total paid same",pre1_p["total_paid"]==post1_p["total_paid"])

ct=post1_p["contracts"][0]
t("Profile: meters",len(ct.get("meter_readings",[]))==4)
t("Profile: bills",len(ct.get("bills",[]))==4)
t("Profile: move_in",ct.get("move_in_inspection")is not None)
t("Profile: move_out",ct.get("move_out_inspection")is not None)
t("Profile: settlement",ct.get("settlement")is not None)
t("Profile: payments",len(ct.get("payments",[]))==3)
t("Profile: items",len(ct.get("items",[]))==3)
t("Profile: settled_at",ct.get("settlement",{}).get("settled_at")is not None)
stl=ct.get("settlement",{})
exp=round(stl.get("deposit_total",0)-stl.get("electricity_deduction",0)-stl.get("item_damage_deduction",0)-stl.get("item_missing_deduction",0)-stl.get("key_deduction",0)-stl.get("unpaid_bills_total",0)-stl.get("other_deduction",0),10)
t(f"Refund {exp}",stl.get("actual_refund")==exp)

print(f"Sample 1: DONE")
