# -*- coding: utf-8 -*-
"""备份服务往返测试：创建快照 → 修改数据 → 恢复 → 验证还原。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.repositories import database as db  # noqa: E402
from app.services.backup import create_snapshot, restore_snapshot, delete_snapshot  # noqa: E402

# 1) 当前用户数
before = db.query_one("SELECT COUNT(*) AS c FROM users")["c"]
print(f"恢复前用户数: {before}")

# 2) 创建快照
snap = create_snapshot("往返测试")
print(f"快照: {snap['name']}")

# 3) 修改数据：插入一个测试用户
import uuid

test_name = f"restore_test_{uuid.uuid4().hex[:6]}"
db.execute(
    "INSERT INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, 'user')",
    (test_name, "x", "y"),
)
after_insert = db.query_one("SELECT COUNT(*) AS c FROM users")["c"]
print(f"插入测试用户后: {after_insert}（应比 {before} 多 1）")

# 4) 恢复快照
result = restore_snapshot(snap["name"])
print(f"恢复: {result['count']} 个文件")

# 5) 验证：测试用户应消失
from app.repositories import users as user_repo

restored_user = user_repo.get_user_by_username(test_name)
after = db.query_one("SELECT COUNT(*) AS c FROM users")["c"]
print(f"恢复后用户数: {after}（应回到 {before}）")
print(f"测试用户存在: {restored_user is not None}（应为 False）")

# 6) 清理快照
delete_snapshot(snap["name"])
print("清理快照完成")

assert after == before, "用户数未还原！"
assert restored_user is None, "测试用户未清除！"
print("\n✅ 往返测试通过：创建→修改→恢复→数据完整还原")
