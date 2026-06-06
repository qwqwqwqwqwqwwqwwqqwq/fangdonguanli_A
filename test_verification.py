import sys, requests, sqlite3
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'http://localhost:8005/api'
HEADERS = {'X-API-Key': 'dev-key-change-me'}

def ok(c):
    return c in (200, 201)

# Find free property and available tenant (skip XSS test data)
props = requests.get(f'{BASE}/properties', headers=HEADERS).json()
free_prop = next(p for p in props if p['status'] == '空闲' and 'script' not in p.get('name','').lower())
tenants = requests.get(f'{BASE}/tenants', headers=HEADERS).json()
avail_tenant = next(t for t in tenants if t['status'] == '在用' and 'script' not in t.get('name','').lower())
print(f'Property: {free_prop["name"]} (ID={free_prop["id"]})')
print(f'Tenant: {avail_tenant["name"]} ({avail_tenant["id_number"]})')

# Step 1: Create contract
print('\n=== Step 1: Create Contract ===')
r = requests.post(f'{BASE}/contracts', headers=HEADERS, json={
    'property_id': free_prop['id'],
    'tenant_id_number': avail_tenant['id_number'],
    'monthly_rent': 2000, 'deposit': 2000, 'rent_due_day': 10,
    'residents_count': 1, 'start_date': '2026-05-01', 'end_date': '2026-12-31',
    'items': [{'item_name': '空调', 'quantity': 1}, {'item_name': '床', 'quantity': 1}]
})
assert ok(r.status_code), f'FAIL: {r.status_code} {r.text}'
c = r.json()
cid = c['id']
print(f'OK: ID={cid} {c["contract_code"]} status={c["status"]}')

# Step 2: Move-in inspection
print('\n=== Step 2: Move-in Inspection ===')
r = requests.post(f'{BASE}/inspections/move-in', headers=HEADERS, json={
    'contract_id': cid, 'inspection_date': '2026-05-01', 'meter_base_reading': 1000
})
assert ok(r.status_code), f'FAIL: {r.status_code} {r.text}'
c2 = requests.get(f'{BASE}/contracts/{cid}', headers=HEADERS).json()
print(f'OK: Contract status -> {c2["status"]}')

# Step 3: Generate bill
print('\n=== Step 3: Generate May Bill ===')
r = requests.post(f'{BASE}/bills/generate/{cid}', headers=HEADERS, json={'bill_month': '2026-05'})
assert r.status_code == 200, f'FAIL: {r.status_code} {r.text}'
bill = r.json()
print(f'OK: {bill["bill_code"]} total={bill["total"]} electricity={bill["electricity_fee"]}')

# Step 4: Meter reading (May)
print('\n=== Step 4: Create Meter Reading (May) ===')
r = requests.post(f'{BASE}/meter-readings/readings', headers=HEADERS, json={
    'contract_id': cid, 'current_reading': 1200, 'reading_date': '2026-05-20'
})
assert ok(r.status_code), f'FAIL: {r.status_code} {r.text}'
reading = r.json()
print(f'OK: {reading["record_code"]} consumption={reading["consumption"]} amount={reading["electricity_amount"]}')

# Verify bill auto-updated
r = requests.get(f'{BASE}/bills/{bill["id"]}', headers=HEADERS).json()
print(f'Bill electricity after reading: {r["electricity_fee"]}')
assert r['electricity_fee'] == 240, f'Expected 240, got {r["electricity_fee"]}'
print('OK: Bill electricity updated to 240')

# Step 5: Duplicate meter reading (should fail)
print('\n=== Step 5: Duplicate Meter Reading (should FAIL) ===')
r = requests.post(f'{BASE}/meter-readings/readings', headers=HEADERS, json={
    'contract_id': cid, 'current_reading': 1300, 'reading_date': '2026-05-25'
})
assert r.status_code == 400, f'Expected 400 for duplicate, got {r.status_code}'
print(f'OK: Rejected - {r.json()["detail"]}')

# Step 6: Pay bill (fetch updated total first)
print('\n=== Step 6: Pay Bill ===')
# Re-fetch bill to get updated total (meter reading auto-updated electricity)
r = requests.get(f'{BASE}/bills/{bill["id"]}', headers=HEADERS)
updated_bill = r.json()
actual_total = updated_bill['total']
print(f'Bill total after meter reading update: {actual_total}')
r = requests.post(f'{BASE}/payments/single', headers=HEADERS, json={
    'bill_id': bill['id'], 'payment_date': '2026-05-20', 'amount': actual_total, 'payment_method': '微信'
})
assert ok(r.status_code), f'FAIL: {r.status_code} {r.text}'
print(f'OK: Paid {actual_total} (full amount)')

# Step 7: Start termination
print('\n=== Step 7: Start Termination ===')
r = requests.post(f'{BASE}/contracts/{cid}/start-termination', headers=HEADERS)
assert ok(r.status_code), f'FAIL: {r.status_code} {r.text}'
print(f'OK: {r.json()["message"]}')

# Step 8: Move-out inspection with keys not returned
print('\n=== Step 8: Move-out Inspection (keys not returned) ===')
r = requests.post(f'{BASE}/inspections/move-out', headers=HEADERS, json={
    'contract_id': cid, 'inspection_date': '2026-05-26', 'meter_reading': 1300,
    'key_return_status': '未归还', 'key_deduction': 200
})
assert ok(r.status_code), f'FAIL: {r.status_code} {r.text}'
insp_out = r.json()
print(f'OK: ID={insp_out["id"]} elec={insp_out["electricity_deduction"]} key_status={insp_out["key_return_status"]} key_ded={insp_out["key_deduction"]}')
assert insp_out['electricity_deduction'] >= 0, f'Electricity is negative! {insp_out["electricity_deduction"]}'

# Step 9: Update items (damage + missing)
print('\n=== Step 9: Update Items ===')
for item in insp_out['items']:
    if item['item_name'] == '空调':
        r = requests.put(f'{BASE}/inspections/move-out/{insp_out["id"]}/items/{item["id"]}', headers=HEADERS, json={'status': '损坏', 'deduction_amount': 300})
        print(f'  空调 -> 损坏 300: {r.status_code}')
    elif item['item_name'] == '床':
        r = requests.put(f'{BASE}/inspections/move-out/{insp_out["id"]}/items/{item["id"]}', headers=HEADERS, json={'status': '缺失', 'deduction_amount': 500})
        print(f'  床 -> 缺失 500: {r.status_code}')

# Step 10: Update key deduction via new endpoint
print('\n=== Step 10: Update Key Deduction ===')
r = requests.put(f'{BASE}/inspections/move-out/{insp_out["id"]}/key-deduction', headers=HEADERS, json={'key_deduction': 300})
assert r.status_code == 200, f'FAIL: {r.status_code} {r.text}'
updated = r.json()
print(f'OK: key_deduction={updated["key_deduction"]}')

# Step 11: Generate settlement
print('\n=== Step 11: Generate Settlement ===')
r = requests.post(f'{BASE}/settlements/{cid}', headers=HEADERS, json={'other_deduction': 100})
assert r.status_code == 200, f'FAIL: {r.status_code} {r.text}'
stl = r.json()
print(f'deposit={stl["deposit_total"]} elec={stl["electricity_deduction"]} damage={stl["item_damage_deduction"]} missing={stl["item_missing_deduction"]} key={stl["key_deduction"]} unpaid={stl["unpaid_bills_total"]} other={stl["other_deduction"]}')
# electricity: (1300-1200)*1.2 = 120
expected_refund = 2000 - 120 - 300 - 500 - 300 - 0 - 100
print(f'actual_refund={stl["actual_refund"]} (expected={expected_refund})')
assert stl['actual_refund'] == expected_refund, f'Refund mismatch! expected {expected_refund}, got {stl["actual_refund"]}'

# Step 12: Confirm settlement
print('\n=== Step 12: Confirm Settlement ===')
r = requests.post(f'{BASE}/settlements/{cid}/confirm', headers=HEADERS, json={'refund_date': '2026-05-26', 'refund_method': '银行转账'})
assert r.status_code == 200, f'FAIL: {r.status_code} {r.text}'
print(f'OK: confirmed')

# Step 13: Verify cleanup
print('\n=== Step 13: Verify Cleanup ===')
r = requests.get(f'{BASE}/contracts/{cid}', headers=HEADERS)
assert r.status_code == 404, f'Contract should be deleted, got {r.status_code}'
print('OK: Contract deleted')

r = requests.get(f'{BASE}/tenants/{avail_tenant["id_number"]}', headers=HEADERS)
assert r.json()['status'] == '已退租', f'Tenant should be archived'
print('OK: Tenant archived')

r = requests.get(f'{BASE}/properties/{free_prop["id"]}', headers=HEADERS)
assert r.json()['status'] == '空闲', f'Property should be free'
print('OK: Property freed')

# Step 14: Test negative electricity rejection
print('\n=== Step 14: Test Negative Electricity Rejection ===')
props2 = requests.get(f'{BASE}/properties', headers=HEADERS).json()
fp2 = next(p for p in props2 if p['status'] == '空闲' and 'script' not in p.get('name','').lower())
t2 = next(t for t in requests.get(f'{BASE}/tenants', headers=HEADERS).json() if t['status'] == '在用' and 'script' not in t.get('name','').lower() and t['id_number'] != avail_tenant['id_number'])
r = requests.post(f'{BASE}/contracts', headers=HEADERS, json={
    'property_id': fp2['id'], 'tenant_id_number': t2['id_number'],
    'monthly_rent': 1500, 'deposit': 1500, 'rent_due_day': 15,
    'start_date': '2026-05-01', 'end_date': '2026-12-31'
})
cid2 = r.json()['id']
requests.post(f'{BASE}/inspections/move-in', headers=HEADERS, json={
    'contract_id': cid2, 'inspection_date': '2026-05-01', 'meter_base_reading': 2000
})
requests.post(f'{BASE}/contracts/{cid2}/start-termination', headers=HEADERS)
r = requests.post(f'{BASE}/inspections/move-out', headers=HEADERS, json={
    'contract_id': cid2, 'inspection_date': '2026-05-26', 'meter_reading': 1500,
    'key_return_status': '已归还', 'key_deduction': 0
})
assert r.status_code == 400, f'Expected 400 for negative electricity, got {r.status_code}'
print(f'OK: Rejected - {r.json()["detail"]}')

# Clean up test contract 2
DB_PATH = r'C:\Users\15157\Desktop\deepseek-V4\房东系统\文件3\backend\landlord.db'
db = sqlite3.connect(DB_PATH)
db.execute('PRAGMA foreign_keys = ON')
db.execute('DELETE FROM move_in_inspection_items WHERE inspection_id IN (SELECT id FROM move_in_inspections WHERE contract_id = ?)', (cid2,))
db.execute('DELETE FROM move_in_inspection_images WHERE inspection_id IN (SELECT id FROM move_in_inspections WHERE contract_id = ?)', (cid2,))
db.execute('DELETE FROM move_in_inspections WHERE contract_id = ?', (cid2,))
db.execute('DELETE FROM contract_items WHERE contract_id = ?', (cid2,))
db.execute('DELETE FROM contracts WHERE id = ?', (cid2,))
db.execute('UPDATE properties SET status = ? WHERE id = ?', ('空闲', fp2['id']))
db.commit()
db.close()

# Check contracts count
r = requests.get(f'{BASE}/contracts', headers=HEADERS)
print(f'\nTotal contracts: {len(r.json())}')

print('\n' + '='*40)
print('ALL 14 TESTS PASSED')
print('='*40)
