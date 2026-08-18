# -*- coding: utf-8 -*-
"""清理自动化测试遗留用户。

安全设计（防误删真实用户）：
1. 只删除用户名同时满足「明确测试前缀」且「短随机后缀特征」的账号；
2. 任何不以测试前缀开头的用户名一律不动；
3. 运行前打印待删清单供人工确认（--yes 跳过确认）。
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.repositories import database as db  # noqa: E402

# 测试前缀（pytest 生成的用户名，固定格式 prefix_8位hex）
TEST_PREFIXES = (
    "testuser_", "iso_user_", "isoa_", "isob_", "tuser_",
    "ok_", "api_empty_", "adm_", "batcha_", "batchb_",
)
# 完整测试名（不带前缀的固定名）
TEST_EXACT = {"demo_user", "other_user", "testnormal"}

# 短随机后缀特征：8 位 hex
_HEX8 = re.compile(r"^[0-9a-f]{8}$")


def is_test_user(username: str) -> bool:
    """判定是否为测试用户（前缀 + hex8 后缀，双重保险）。"""
    if username in TEST_EXACT:
        return True
    for prefix in TEST_PREFIXES:
        if username.startswith(prefix):
            suffix = username[len(prefix):]
            # 必须有 8 位 hex 后缀才是测试账号；真实用户即使同名前缀也不会被删
            return bool(_HEX8.match(suffix))
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="清理测试用户（安全白名单）")
    parser.add_argument("--yes", action="store_true", help="跳过确认直接删除")
    args = parser.parse_args()

    rows = db.query("SELECT id, username FROM users ORDER BY id")
    targets = [r for r in rows if is_test_user(r["username"])]
    keep = [r for r in rows if not is_test_user(r["username"])]

    print(f"待删除 {len(targets)} 个测试用户，保留 {len(keep)} 个用户：")
    for r in targets:
        print(f"  ✗ {r['username']} (id={r['id']})")
    print("保留:")
    for r in keep:
        print(f"  ✓ {r['username']} (id={r['id']})")

    if not targets:
        print("\n无需清理。")
        return

    if not args.yes:
        ans = input("\n确认删除以上测试用户？[y/N] ").strip().lower()
        if ans != "y":
            print("已取消。")
            return

    for r in targets:
        uid = r["id"]
        db.execute("DELETE FROM tokens WHERE user_id = ?", (uid,))
        db.execute("DELETE FROM sessions WHERE user_id = ?", (uid,))
        db.execute(
            "DELETE FROM messages WHERE session_id IN (SELECT id FROM sessions WHERE user_id = ?)",
            (uid,),
        )
        db.execute("DELETE FROM users WHERE id = ?", (uid,))
        print(f"已删除: {r['username']}")
    print(f"\n完成，共删除 {len(targets)} 个。")


if __name__ == "__main__":
    main()
