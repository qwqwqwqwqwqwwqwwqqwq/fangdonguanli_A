import requests; H={'X-API-Key':'dev-key-change-me'}; r=requests.get('http://localhost:8005/api/properties', headers=H); print(f'status={r.status_code}')
