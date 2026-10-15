"""场景分类目录 API（52 一级分类占位）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.auth import get_current_user
from app.schemas.scene import SceneCatalogItem, SceneCatalogOut
from app.services import scenes_catalog as catalog_svc

router = APIRouter(prefix="/api", tags=["scenes"])


@router.get("/scenes", response_model=SceneCatalogOut)
def list_scenes(
    status: str | None = Query(None, description="可选过滤：active|coming_soon"),
    _: dict = Depends(get_current_user),
) -> SceneCatalogOut:
    data = catalog_svc.catalog_summary()
    items = data["items"]
    if status:
        items = [x for x in items if x.get("status") == status]
    return SceneCatalogOut(
        version=int(data.get("version") or 1),
        total=len(items) if status else int(data["total"]),
        active_count=int(data["active_count"]),
        coming_soon_count=int(data["coming_soon_count"]),
        mvp_ids=list(data.get("mvp_ids") or []),
        groups=dict(data.get("groups") or {}),
        items=[
            SceneCatalogItem(
                id=x.get("id") or "",
                name=x.get("name") or x.get("id") or "",
                group=x.get("group") or "",
                status=x.get("status") or "coming_soon",
                alias=x.get("alias") or "",
            )
            for x in items
        ],
    )
