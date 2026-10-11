"""M0 基建烟测：MySQL ping + /api/health + 注册登录。

前置：MySQL 已启动（可用 docker compose -f deploy/docker-compose.yml up -d mysql）
用法：
  pip install -r requirements.txt
  python scripts/smoke_m0.py
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.repositories import database as db  # noqa: E402


def main() -> int:
    print("1) init_db + ping ...")
    db.init_db()
    assert db.ping(), "MySQL ping 失败"
    print("   MySQL OK")

    client = TestClient(app)
    print("2) GET /api/health ...")
    r = client.get("/api/health")
    assert r.status_code == 200, r.text
    body = r.json()
    print("  ", body)
    assert body.get("mysql") is True, body

    name = f"smoke_{uuid.uuid4().hex[:8]}"
    print(f"3) register/login {name} ...")
    r = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    r = client.post("/api/auth/login", json={"username": name, "password": "pass1234"})
    assert r.status_code == 200, r.text
    assert r.json()["token"]
    print("   auth OK, token len=", len(token))

    print("M0 smoke PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
