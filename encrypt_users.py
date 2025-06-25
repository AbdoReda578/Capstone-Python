import json
from werkzeug.security import generate_password_hash

with open('users.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for user in data.get('users', []):
    pwd = user['password']
    if not pwd.startswith('pbkdf2:'):
        user['password'] = generate_password_hash(pwd)

with open('users.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("✔️ تم تشفير كل الباسوردات.")
