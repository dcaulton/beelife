from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from beelife.db.models import Device
from beelife.db.repositories import DeviceRepository
from beelife.db.session import get_db

router = APIRouter(prefix="/devices", tags=["devices"])


def get_device_repo(db: Annotated[AsyncSession, Depends(get_db)]) -> DeviceRepository:
    return DeviceRepository(db)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_device(
    device: Device,
    repo: Annotated[DeviceRepository, Depends(get_device_repo)],
) -> Device:
    return await repo.create(device)


@router.get("")
async def list_devices(
    repo: Annotated[DeviceRepository, Depends(get_device_repo)],
    active_only: bool = True,
) -> list[Device]:
    return await repo.list(active_only=active_only)


@router.get("/{device_id}")
async def get_device(
    device_id: str,
    repo: Annotated[DeviceRepository, Depends(get_device_repo)],
) -> Device:
    device = await repo.get(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.patch("/{id}")
async def update_device(
    id: UUID,
    updates: dict,
    repo: Annotated[DeviceRepository, Depends(get_device_repo)],
) -> Device:
    device = await repo.get_by_id(id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    for key, value in updates.items():
        if hasattr(device, key):
            setattr(device, key, value)

    return await repo.update(device)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    id: UUID,
    repo: Annotated[DeviceRepository, Depends(get_device_repo)],
) -> None:
    success = await repo.soft_delete(id)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")
