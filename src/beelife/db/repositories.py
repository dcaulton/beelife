from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from beelife.db.models import BeeDarReading, WeatherObservation


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
