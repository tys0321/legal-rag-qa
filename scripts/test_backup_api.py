# -*- coding: utf-8 -*-
"""通过 API 验证快照恢复：创建快照 → 删除用户 → 恢复 → 用户还原。"""
import sys
import urllib.parse
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

BASE = "http://127.0.0.1:8000"
sess = requests.Session()

# 登录 admin
r = sess.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "admin123"})
token = r.json()["token"]
sess.headers["Authorization"] = f"Bearer {token}"

# 1) 创建快照
r = sess.post(f"{BASE}/api/admin/backup/create", params={"description": "API恢复验证"})
assert r.status_code == 200, r.text
snap = r.json()["name"]
print(f"① 创建快照: {snap} ({r.json()['size_mb']} MB)")

# 2) 删除一个用户（usertwo）
r = sess.post(f"{BASE}/api/admin/users/62/delete")
print(f"② 删除 usertwo: HTTP {r.status_code}")

# 3) 确认用户没了
r = sess.get(f"{BASE}/api/admin/users")
names = [u["username"] for u in r.json()["users"]]
print(f"   删除后用户: {names}")

# 4) 恢复快照
r = sess.post(f"{BASE}/api/admin/backup/{snap}/restore")
print(f"③ 恢复快照: HTTP {r.status_code} count={r.json().get('count')}")

# 5) 验证 usertwo 回来了
r = sess.get(f"{BASE}/api/admin/users")
names_after = [u["username"] for u in r.json()["users"]]
print(f"④ 恢复后用户: {names_after}")
print(f"   usertwo 回来了: {'usertwo' in names_after}")

# 6) 清理快照
r = sess.delete(f"{BASE}/api/admin/backup/{snap}")
print(f"⑤ 清理快照: HTTP {r.status_code}")

assert "usertwo" in names_after, "恢复失败：usertwo 未还原！"
print("\n✅ API 恢复验证通过：创建→删除用户→恢复→用户完整还原")
