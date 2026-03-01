from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from services.site_config_service import SiteConfigService, get_site_config_service
from schemas.site_config_schema import SiteConfigIn, SiteConfigOut

router = APIRouter(prefix="/site-config", tags=["SiteConfig"])


# 1. Загрузить новый конфиг
@router.post("/", response_model=SiteConfigOut, status_code=status.HTTP_201_CREATED)
async def save_config(
    data: SiteConfigIn,
    service: SiteConfigService = Depends(get_site_config_service),
):
    return await service.save_config(data)


# 2. Получить последний конфиг в виде JSON
@router.get("/latest", response_model=Dict[str, Any])
async def get_latest_config(
    service: SiteConfigService = Depends(get_site_config_service),
):
    try:
        return await service.get_latest_config()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# 3. Удалить все конфиги кроме последнего
@router.delete("/cleanup", status_code=status.HTTP_200_OK)
async def delete_all_except_latest(
    service: SiteConfigService = Depends(get_site_config_service),
):
    try:
        deleted_count = await service.delete_all_except_latest()
        return {"deleted": deleted_count}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
