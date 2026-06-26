from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from beelife.db.models import BeeDarReading, Device, WeatherObservation


async def get_default_device(session: AsyncSession) -> Device | None:
    """Return the only active device if exactly one exists, otherwise None."""
    repo = DeviceRepository(session)
    devices = await repo.list(active_only=True)
    if len(devices) == 1:
        return devices[0]
    return None


class BeeDarRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_many(self, readings: list[BeeDarReading]) -> list[BeeDarReading]:
        if not readings:
            return []

        stmt = (
            insert(BeeDarReading)
            .values([r.model_dump() for r in readings])
            .on_conflict_do_nothing(index_elements=["timestamp"])
        )

        await self.session.execute(stmt)
        await self.session.commit()
        return readings

    async def get_by_device_and_time(self, device_id: str, start: datetime, end: datetime) -> list[BeeDarReading]:
        stmt = (
            select(BeeDarReading)
            .where(BeeDarReading.device_id == device_id)  # type: ignore[arg-type]
            .where(BeeDarReading.timestamp >= start)  # type: ignore[arg-type]
            .where(BeeDarReading.timestamp <= end)  # type: ignore[arg-type]
            .order_by(BeeDarReading.timestamp)  # type: ignore[arg-type]
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class WeatherRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_many(self, observations: list[WeatherObservation]) -> list[WeatherObservation]:
        self.session.add_all(observations)
        await self.session.commit()
        for obs in observations:
            await self.session.refresh(obs)
        return observations

    async def get_by_time_range(self, start: datetime, end: datetime) -> list[WeatherObservation]:
        stmt = (
            select(WeatherObservation)
            .where(WeatherObservation.timestamp >= start)  # type: ignore[arg-type]
            .where(WeatherObservation.timestamp <= end)  # type: ignore[arg-type]
            .order_by(WeatherObservation.timestamp)  # type: ignore[arg-type]
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class DeviceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, device: Device) -> Device:
        self.session.add(device)
        await self.session.commit()
        await self.session.refresh(device)
        return device

    async def get(self, device_id: str) -> Device | None:
        stmt = select(Device).where(Device.device_id == device_id)  # type: ignore[arg-type]
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, id: UUID) -> Device | None:
        stmt = select(Device).where(Device.id == id)  # type: ignore[arg-type]
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, device: Device) -> Device:
        await self.session.commit()
        await self.session.refresh(device)
        return device

    async def delete(self, device: Device) -> None:
        await self.session.delete(device)
        await self.session.commit()

    async def soft_delete(self, device_id: UUID) -> bool:
        stmt = (
            update(Device)
            .where(Device.id == device_id)  # type: ignore[arg-type]
            .values(is_active=False)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return bool(result.rowcount)  # type: ignore[attr-defined]

    async def list(self, active_only: bool = True) -> list[Device]:
        stmt = select(Device)
        if active_only:
            stmt = stmt.where(Device.is_active.is_(True))  # type: ignore[attr-defined]
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
