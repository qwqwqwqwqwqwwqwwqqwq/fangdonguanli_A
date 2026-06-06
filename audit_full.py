"""Comprehensive audit: 2 samples, compare pre vs post settlement data."""
import requests, random, string, sys, json, datetime
sys.stdout.reconfigure(encoding='utf-8')
B = 'http://localhost:8005/api'; H = {'X-API-Key': 'dev-key-change-me'}
def ok(r): return r.status_code in (200, 201)
def randid(): return '990' + ''.join(random.choice(string.digits) for _ in range(15))
def randphone(): return '138' + ''.join(random.choice(string.digits) for _ in range(8))

P = F = 0
def t(n, c, d=''):
    global P, F
    if c: P += 1; print(f'  PASS: {n}')
    else: F += 1; print(f'  FAIL: {n}  {d}')

print('='*60)
print('  COMPREHENSIVE DATA INTEGRITY AUDIT')
print('  2 Samples: Pre vs Post Settlement Comparison')
print('='*60)

# ============================================================
# SAMPLE 1: Normal tenant, full cycle, 4 months
# ============================================================
print('\n### SAMPLE 1: Normal Tenant (4 months, 3 payments, 1 damage) ###')
s1 = ''.join(random.choice(string.digits) for _ in range(4))

# Create
r = requests.post(B+'/properties', headers=H, json={'name':f'A1-{s1}','address':f'Addr1-{s1}','status':'空闲'})
assert ok(r); pid1 = r.json()['id']; IDLE = r.json()['status']
r = requests.post(B+'/tenants', headers=H, json={'id_number':randid(),'name':f'Zhang-{s1}','phone':randphone()})
assert ok(r); tid1 = r.json()['id_number']; ACTIVE = r.json()['status']
r = requests.post(B+'/contracts', headers=H, json={
    'property_id':pid1,'tenant_id_number':tid1,'monthly_rent':2500,'deposit':3000,
    'rent_due_day':5,'residents_count':2,'water_fee':60,
    'start_date':'2026-01-01','end_date':'2026-06-30',
    'items':[{'item_name':'空调','quantity':2},{'item_name':'双人床','quantity':1},{'item_name':'冰箱','quantity':1}]})
assert ok(r); cid1 = r.json()['id']; cc1 = r.json()['contract_code']
print(f'  Contract: {cc1} (ID={cid1})  Tenant: {tid1}')

# Move-in
requests.post(B+'/inspections/move-in', headers=H, json={'contract_id':cid1,'inspection_date':'2026-01-01','meter_base_reading':500})
# 4 meter readings
for dt,rd in [('2026-01-25',800),('2026-02-22',1100),('2026-03-25',1450),('2026-04-26',1800)]:
    requests.post(B+'/meter-readings/readings', headers=H, json={'contract_id':cid1,'current_reading':rd,'reading_date':dt})
# 4 bills
bids1 = []
for m in ['2026-01','2026-02','2026-03','2026-04']:
    r = requests.post(B+f'/bills/generate/{cid1}', headers=H, json={'bill_month':m})
    bids1.append(r.json()['id'])
# 3 payments: Jan full, Feb full, Mar partial
for i, (bid, amt) in enumerate([(bids1[0],2860),(bids1[1],2980),(bids1[2],2000)]):
    requests.post(B+'/payments/single', headers=H, json={'bill_id':bid,'payment_date':f'2026-0{i+1}-27','amount':amt,'payment_method':'微信'})

# PRE-SETTLEMENT SNAPSHOT
pre1_p = requests.get(B+f'/tenants/{tid1}/profile', headers=H).json()
pre1_m = len(requests.get(B+f'/meter-readings/contracts/{cid1}/readings', headers=H).json())
pre1_b = len(requests.get(B+'/bills', headers=H, params={'contract_id':cid1}).json())
pre1_ct = requests.get(B+f'/contracts/{cid1}', headers=H).json()
pre1_ten = requests.get(B+f'/tenants/{tid1}', headers=H).json()
pre1_prop = requests.get(B+f'/properties/{pid1}', headers=H).json()

print(f'  PRE: tenant={pre1_ten["status"]} contract={pre1_ct["status"]} prop={pre1_prop["status"]}')
print(f'  PRE: total_billed={pre1_p["total_billed"]} total_paid={pre1_p["total_paid"]} meters={pre1_m} bills={pre1_b}')

# Move-out + settlement
requests.post(B+f'/contracts/{cid1}/start-termination', headers=H)
r = requests.post(B+'/inspections/move-out', headers=H, json={'contract_id':cid1,'inspection_date':'2026-05-01','meter_reading':1800,'key_return_status':'已归还','key_deduction':0})
insp1 = r.json() if r.status_code in (200,201) else {}
if insp1:
    for item in insp1.get('items',[]):
        st = '损坏' if item['item_name']=='冰箱' else '完好'
        da = 300 if item['item_name']=='冰箱' else 0
        requests.put(B+f'/inspections/move-out/{insp1["id"]}/items/{item["id"]}', headers=H, json={'status':st,'deduction_amount':da})

r = requests.post(B+f'/settlements/{cid1}', headers=H, json={'other_deduction':0})
assert r.status_code==200
r = requests.post(B+f'/settlements/{cid1}/confirm', headers=H, json={'refund_date':'2026-05-15','refund_method':'银行转账'})
assert r.status_code==200
print(f'  Settlement confirmed')

# POST-SETTLEMENT SNAPSHOT
post1_p = requests.get(B+f'/tenants/{tid1}/profile', headers=H).json()
post1_m = len(requests.get(B+f'/meter-readings/contracts/{cid1}/readings', headers=H).json())
post1_b = len(requests.get(B+'/bills', headers=H, params={'contract_id':cid1}).json())
post1_ct = requests.get(B+f'/contracts/{cid1}', headers=H).json()
post1_ten = requests.get(B+f'/tenants/{tid1}', headers=H).json()
post1_prop = requests.get(B+f'/properties/{pid1}', headers=H).json()

print(f'  POST: tenant={post1_ten["status"]} contract={post1_ct["status"]} prop={post1_prop["status"]}')
print(f'  POST: total_billed={post1_p["total_billed"]} total_paid={post1_p["total_paid"]} meters={post1_m} bills={post1_b}')

# VERIFY S1
t('S1: Tenant archived', post1_ten['status']=='已退租', post1_ten['status'])
t('S1: Contract settled', '已结算' in post1_ct['status'], post1_ct['status'])
t('S1: Property freed', post1_prop['status']==IDLE, post1_prop['status'])
t('S1: Bills count preserved', pre1_b==post1_b, f'{pre1_b} vs {post1_b}')
t('S1: Meters count preserved', pre1_m==post1_m, f'{pre1_m} vs {post1_m}')
t('S1: total_billed preserved', pre1_p['total_billed']==post1_p['total_billed'])
t('S1: total_paid preserved', pre1_p['total_paid']==post1_p['total_paid'])
ct = post1_p['contracts'][0] if post1_p['contracts'] else {}
t('S1: Profile has meter_readings(4)', len(ct.get('meter_readings',[]))==4, str(len(ct.get('meter_readings',[]))))
t('S1: Profile has bills(4)', len(ct.get('bills',[]))==4)
t('S1: Profile has move_in', ct.get('move_in_inspection') is not None)
t('S1: Profile has move_out', ct.get('move_out_inspection') is not None)
t('S1: Profile has settlement', ct.get('settlement') is not None)
t('S1: Profile has payments(3)', len(ct.get('payments',[]))==3, str(len(ct.get('payments',[]))))
t('S1: Profile has items(3)', len(ct.get('items',[]))==3)
t('S1: Profile has settled_at', ct.get('settlement',{}).get('settled_at') is not None)
# Verify refund formula
stl = ct.get('settlement',{})
exp = round(stl.get('deposit_total',0)-stl.get('electricity_deduction',0)-stl.get('item_damage_deduction',0)-stl.get('item_missing_deduction',0)-stl.get('key_deduction',0)-stl.get('unpaid_bills_total',0)-stl.get('other_deduction',0),10)
t('S1: Refund formula correct', stl.get('actual_refund')==exp, f'expected {exp} got {stl.get("actual_refund")}')

S1_PASS = P; S1_FAIL = F

# ============================================================
# SAMPLE 2: Complex tenant, damages, partial payment, key not returned
# ============================================================
print('\n### SAMPLE 2: Complex Tenant (damages, missing items, key not returned) ###')
P2 = F2 = 0
def t2(n, c, d=''):
    global P2, F2
    if c: P2 += 1; print(f'  PASS: {n}')
    else: F2 += 1; print(f'  FAIL: {n}  {d}')

s2 = ''.join(random.choice(string.digits) for _ in range(4))
r = requests.post(B+'/properties', headers=H, json={'name':f'A2-{s2}','address':f'Addr2-{s2}','status':'空闲'})
assert ok(r); pid2 = r.json()['id']
r = requests.post(B+'/tenants', headers=H, json={'id_number':randid(),'name':f'Li-{s2}','phone':randphone()})
assert ok(r); tid2 = r.json()['id_number']
r = requests.post(B+'/contracts', headers=H, json={
    'property_id':pid2,'tenant_id_number':tid2,'monthly_rent':1800,'deposit':1800,
    'rent_due_day':15,'residents_count':1,'water_fee':30,
    'start_date':'2026-03-01','end_date':'2026-05-31',
    'items':[{'item_name':'洗衣机','quantity':1},{'item_name':'电视','quantity':1},{'item_name':'沙发','quantity':1}]})
assert ok(r); cid2 = r.json()['id']; cc2 = r.json()['contract_code']
print(f'  Contract: {cc2} (ID={cid2})  Tenant: {tid2}')

requests.post(B+'/inspections/move-in', headers=H, json={'contract_id':cid2,'inspection_date':'2026-03-01','meter_base_reading':200})
for dt,rd in [('2026-03-28',500),('2026-04-25',750)]:
    requests.post(B+'/meter-readings/readings', headers=H, json={'contract_id':cid2,'current_reading':rd,'reading_date':dt})
bids2 = []
for m in ['2026-03','2026-04']:
    r = requests.post(B+f'/bills/generate/{cid2}', headers=H, json={'bill_month':m})
    bids2.append(r.json()['id'])
# Mar full, Apr partial 500
requests.post(B+'/payments/single', headers=H, json={'bill_id':bids2[0],'payment_date':'2026-03-28','amount':2190,'payment_method':'银行转账'})
requests.post(B+'/payments/single', headers=H, json={'bill_id':bids2[1],'payment_date':'2026-04-28','amount':500,'payment_method':'微信'})

pre2_p = requests.get(B+f'/tenants/{tid2}/profile', headers=H).json()
pre2_m = len(requests.get(B+f'/meter-readings/contracts/{cid2}/readings', headers=H).json())
pre2_b = len(requests.get(B+'/bills', headers=H, params={'contract_id':cid2}).json())
print(f'  PRE: total_billed={pre2_p["total_billed"]} total_paid={pre2_p["total_paid"]} meters={pre2_m} bills={pre2_b}')

requests.post(B+f'/contracts/{cid2}/start-termination', headers=H)
r = requests.post(B+'/inspections/move-out', headers=H, json={'contract_id':cid2,'inspection_date':'2026-05-01','meter_reading':750,'key_return_status':'未归还','key_deduction':200})
insp2 = r.json() if r.status_code in (200,201) else {}
if insp2:
    for item in insp2.get('items',[]):
        if item['item_name']=='洗衣机': st,da = '损坏',500
        elif item['item_name']=='电视': st,da = '缺失',800
        else: st,da = '完好',0
        requests.put(B+f'/inspections/move-out/{insp2["id"]}/items/{item["id"]}', headers=H, json={'status':st,'deduction_amount':da})

r = requests.post(B+f'/settlements/{cid2}', headers=H, json={'other_deduction':150})
assert r.status_code==200; stl2 = r.json()
print(f'  Settlement: damage={stl2["item_damage_deduction"]} missing={stl2["item_missing_deduction"]} key={stl2["key_deduction"]} other={stl2["other_deduction"]} refund={stl2["actual_refund"]}')
r = requests.post(B+f'/settlements/{cid2}/confirm', headers=H, json={'refund_date':'2026-05-15','refund_method':'支付宝'})
assert r.status_code==200

post2_p = requests.get(B+f'/tenants/{tid2}/profile', headers=H).json()
post2_m = len(requests.get(B+f'/meter-readings/contracts/{cid2}/readings', headers=H).json())
post2_b = len(requests.get(B+'/bills', headers=H, params={'contract_id':cid2}).json())
post2_ct = requests.get(B+f'/contracts/{cid2}', headers=H).json()
post2_ten = requests.get(B+f'/tenants/{tid2}', headers=H).json()
post2_prop = requests.get(B+f'/properties/{pid2}', headers=H).json()

print(f'  POST: tenant={post2_ten["status"]} contract={post2_ct["status"]} prop={post2_prop["status"]}')

# VERIFY S2
t2('S2: Tenant archived', post2_ten['status']=='已退租')
t2('S2: Contract settled', '已结算' in post2_ct['status'])
t2('S2: Property freed', post2_prop['status']==IDLE)
t2('S2: Bills preserved', pre2_b==post2_b, f'{pre2_b} vs {post2_b}')
t2('S2: Meters preserved', pre2_m==post2_m)
t2('S2: total_billed preserved', pre2_p['total_billed']==post2_p['total_billed'])
t2('S2: total_paid preserved', pre2_p['total_paid']==post2_p['total_paid'])

ct2 = post2_p['contracts'][0] if post2_p['contracts'] else {}
t2('S2: Profile meters(2)', len(ct2.get('meter_readings',[]))==2)
t2('S2: Profile bills(2)', len(ct2.get('bills',[]))==2)
t2('S2: Profile move_in', ct2.get('move_in_inspection') is not None)
t2('S2: Profile move_out', ct2.get('move_out_inspection') is not None)
t2('S2: Profile settlement', ct2.get('settlement') is not None)
t2('S2: Profile payments(2)', len(ct2.get('payments',[]))==2, str(len(ct2.get('payments',[]))))
t2('S2: Profile items(3)', len(ct2.get('items',[]))==3)
t2('S2: settled_at', ct2.get('settlement',{}).get('settled_at') is not None)

# Verify damage details preserved
mo = ct2.get('move_out_inspection',{})
mo_items = mo.get('items',[])
damaged = [i for i in mo_items if i.get('status')=='损坏']
missing = [i for i in mo_items if i.get('status')=='缺失']
ok_items = [i for i in mo_items if i.get('status')=='完好']
t2('S2: 1 damaged', len(damaged)==1)
t2('S2: 1 missing', len(missing)==1)
t2('S2: 1 ok', len(ok_items)==1)
t2('S2: Key not returned', mo.get('key_return_status')=='未归还')
t2('S2: Key deduction=200', mo.get('key_deduction')==200)
stl2c = ct2.get('settlement',{})
t2('S2: Damage=500', stl2c.get('item_damage_deduction')==500)
t2('S2: Missing=800', stl2c.get('item_missing_deduction')==800)
t2('S2: Other=150', stl2c.get('other_deduction')==150)
t2('S2: Key in stl=200', stl2c.get('key_deduction')==200)

# ============================================================
# FINAL SUMMARY
# ============================================================
print(f'\n{"="*60}')
print(f'  AUDIT RESULTS')
print(f'{"="*60}')
print(f'  Sample 1 ({cc1}): {S1_PASS}P {S1_FAIL}F')
print(f'  Sample 2 ({cc2}): {P2}P {F2}F')
print(f'  TOTAL: {P + P2} PASS, {F + F2} FAIL')
print(f'{"="*60}')
sys.exit(0 if (F + F2) == 0 else 1)
