import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from beelife.db.models import Device
from beelife.db.repositories import DeviceRepository, get_default_device


@pytest.mark.asyncio
async def test_create_and_get_device(async_session: AsyncSession) -> None:
    repo = DeviceRepository(async_session)

    device = Device(
        device_id="63:02:21",
        name="Main BeeDar",
        type="beedar",
        location_name="Home Apiary",
        latitude=41.85,
        longitude=-87.65,
    )

    created = await repo.create(device)
    assert created.id is not None
    assert created.device_id == "63:02:21"

    fetched = await repo.get("63:02:21")
    assert fetched is not None
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_list_devices(async_session: AsyncSession) -> None:
    repo = DeviceRepository(async_session)

    await repo.create(Device(device_id="63:02:21", name="BeeDar 1"))
    await repo.create(Device(device_id="63:02:22", name="BeeDar 2", is_active=False))

    all_devices = await repo.list(active_only=False)
    active_devices = await repo.list(active_only=True)

    assert len(all_devices) == 2
    assert len(active_devices) == 1


@pytest.mark.asyncio
async def test_update_device(async_session: AsyncSession) -> None:
    repo = DeviceRepository(async_session)

    device = await repo.create(Device(device_id="63:02:21", name="Old Name"))
    device.name = "Updated Name"

    updated = await repo.update(device)
    assert updated.name == "Updated Name"


@pytest.mark.asyncio
async def test_delete_device(async_session: AsyncSession) -> None:
    repo = DeviceRepository(async_session)

    device = await repo.create(Device(device_id="63:02:21"))
    await repo.delete(device)

    result = await repo.get("63:02:21")
    assert result is None


@pytest.mark.asyncio
async def test_get_default_device_single_device(async_session: AsyncSession) -> None:
    repo = DeviceRepository(async_session)
    await repo.create(Device(device_id="63:02:21", name="Only Device"))

    default = await get_default_device(async_session)
    assert default is not None
    assert default.device_id == "63:02:21"


@pytest.mark.asyncio
async def test_get_default_device_multiple_devices(async_session: AsyncSession) -> None:
    repo = DeviceRepository(async_session)
    await repo.create(Device(device_id="63:02:21"))
    await repo.create(Device(device_id="63:02:22"))

    default = await get_default_device(async_session)
    assert default is None
