"""Regression tests for critical backend isolation and configuration paths."""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import delete, select

from app.modules.knowledge_base.models import KnowledgeBaseDB  # noqa: F401
from app.modules.subscriptions.models import UserSubscriptionDB
from app.modules.whatsapp import service as whatsapp_service
from app.modules.whatsapp.models import WhatsAppDeviceDB

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
ORDER_ISOLATION_DEVICE_ID = "order-isolation-regression"


async def test_orphan_cleanup_preserves_every_registered_device(db_session):
    """Cleanup compares GOWA against devices registered by every user."""
    suffix = uuid.uuid4().hex
    current_user_device = WhatsAppDeviceDB(
        user_id=TEST_USER_ID,
        device_id=f"current-user-device-{suffix}",
    )
    other_user_device = WhatsAppDeviceDB(
        user_id="a-different-user",
        device_id=f"other-user-device-{suffix}",
    )
    orphaned = f"genuine-orphan-{suffix}"
    db_session.add_all([current_user_device, other_user_device])
    await db_session.commit()

    try:
        with (
            patch.object(
                whatsapp_service.gowa_client,
                "list_devices",
                new=AsyncMock(
                    return_value=[
                        {"id": other_user_device.device_id},
                        {"id": orphaned},
                    ]
                ),
            ),
            patch.object(
                whatsapp_service,
                "_force_remove_device_from_gowa",
                new=AsyncMock(return_value=True),
            ) as remove_device,
        ):
            cleaned = await whatsapp_service._cleanup_orphaned_devices(db_session)

        assert cleaned == 1
        remove_device.assert_awaited_once_with(orphaned)
    finally:
        await db_session.delete(current_user_device)
        await db_session.delete(other_user_device)
        await db_session.commit()


async def test_manual_orphan_cleanup_is_not_available_to_ordinary_user(client):
    with (
        patch("app.core.dependencies.settings.ADMIN_EMAILS", "admin@example.com"),
        patch(
            "app.core.dependencies.decode_firebase_token",
            new=AsyncMock(
                return_value={
                    "uid": TEST_USER_ID,
                    "email": "user@example.com",
                    "email_verified": True,
                }
            ),
        ),
    ):
        response = await client.post(
            "/whatsapp/devices/cleanup/orphaned",
            headers={"Authorization": "Bearer ordinary-user-token"},
        )

    assert response.status_code == 404


async def test_delete_device_cannot_remove_another_users_device(client, db_session):
    other_users_device = WhatsAppDeviceDB(
        user_id="a-different-user",
        device_id=f"cross-tenant-delete-{uuid.uuid4().hex}",
    )
    db_session.add(other_users_device)
    await db_session.commit()

    with (
        patch.object(
            whatsapp_service.gowa_client,
            "get_device_info",
            new=AsyncMock(),
        ) as get_device_info,
        patch.object(
            whatsapp_service,
            "_force_remove_device_from_gowa",
            new=AsyncMock(return_value=True),
        ) as remove_device,
    ):
        response = await client.delete(f"/whatsapp/devices/{other_users_device.device_id}")

    assert response.status_code == 404
    get_device_info.assert_not_awaited()
    remove_device.assert_not_awaited()
    await db_session.refresh(other_users_device)


async def test_delete_unknown_device_does_not_call_gowa(db_session):
    unknown_device_id = f"unknown-device-{uuid.uuid4().hex}"

    with (
        patch.object(
            whatsapp_service.gowa_client,
            "get_device_info",
            new=AsyncMock(),
        ) as get_device_info,
        patch.object(
            whatsapp_service,
            "_force_remove_device_from_gowa",
            new=AsyncMock(return_value=True),
        ) as remove_device,
    ):
        deleted = await whatsapp_service.delete_device(db_session, unknown_device_id, TEST_USER_ID)

    assert deleted is False
    get_device_info.assert_not_awaited()
    remove_device.assert_not_awaited()


async def test_create_device_rejects_user_at_plan_limit(client, db_session):
    existing_device = WhatsAppDeviceDB(
        user_id=TEST_USER_ID,
        device_id=f"at-plan-limit-{uuid.uuid4().hex}",
    )
    db_session.add(existing_device)
    await db_session.commit()

    try:
        with (
            patch(
                "app.modules.whatsapp.router.get_device_limit",
                new=AsyncMock(return_value=1),
            ),
            patch(
                "app.modules.whatsapp.router.service.create_device",
                new=AsyncMock(),
            ) as create_device,
        ):
            response = await client.post(
                "/whatsapp/devices", json={"name": "Extra device"}
            )

        assert response.status_code == 403
        assert "(1 device)" in response.json()["detail"]
        create_device.assert_not_awaited()
    finally:
        await db_session.delete(existing_device)
        await db_session.commit()


async def test_concurrent_device_creation_respects_plan_limit(client, db_session):
    """The per-user transaction lock prevents two GOWA device creations."""
    created_device_ids = []

    async def create_and_commit(db, user_id, name):
        device_id = f"concurrent-{uuid.uuid4().hex}"
        db.add(
            WhatsAppDeviceDB(
                user_id=user_id,
                device_id=device_id,
                name=name,
                status="pending",
            )
        )
        await asyncio.sleep(0.05)
        await db.commit()
        created_device_ids.append(device_id)

        device = MagicMock()
        device.model_dump.return_value = {"device_id": device_id}
        qr = MagicMock()
        qr.model_dump.return_value = {"device_id": device_id}
        return device, qr

    try:
        with (
            patch(
                "app.modules.whatsapp.router.get_device_limit",
                new=AsyncMock(return_value=1),
            ),
            patch(
                "app.modules.whatsapp.router.service.create_device",
                new=AsyncMock(side_effect=create_and_commit),
            ) as create_device,
        ):
            responses = await asyncio.gather(
                client.post("/whatsapp/devices", json={"name": "First"}),
                client.post("/whatsapp/devices", json={"name": "Second"}),
            )

        assert sorted(response.status_code for response in responses) == [201, 403]
        assert create_device.await_count == 1
        assert len(created_device_ids) == 1
    finally:
        await db_session.execute(
            delete(WhatsAppDeviceDB).where(
                WhatsAppDeviceDB.device_id.in_(created_device_ids)
            )
        )
        await db_session.commit()


async def test_initial_subscription_creation_is_serialized(client, db_session):
    """The first two device requests cannot race the unique subscription insert."""

    async def create_and_commit(db, user_id, name):
        device_id = f"initial-subscription-{uuid.uuid4().hex}"
        db.add(
            WhatsAppDeviceDB(
                user_id=user_id,
                device_id=device_id,
                name=name,
                status="pending",
            )
        )
        await asyncio.sleep(0.05)
        await db.commit()

        device = MagicMock()
        device.model_dump.return_value = {"device_id": device_id}
        qr = MagicMock()
        qr.model_dump.return_value = {"device_id": device_id}
        return device, qr

    with patch(
        "app.modules.whatsapp.router.service.create_device",
        new=AsyncMock(side_effect=create_and_commit),
    ) as create_device:
        responses = await asyncio.gather(
            client.post("/whatsapp/devices", json={"name": "First"}),
            client.post("/whatsapp/devices", json={"name": "Second"}),
        )

    assert sorted(response.status_code for response in responses) == [201, 403]
    assert create_device.await_count == 1
    subscriptions = await db_session.execute(
        select(UserSubscriptionDB).where(UserSubscriptionDB.user_id == TEST_USER_ID)
    )
    assert len(subscriptions.scalars().all()) == 1


async def test_global_gowa_lock_protects_in_flight_devices(_session_factory):
    """Creates for different users and cleanup share one global GOWA lock."""
    first_add_started = asyncio.Event()
    release_first_add = asyncio.Event()
    gowa_device_ids = []
    removed_device_ids = []

    async def add_device(name: str):
        device_id = f"global-lock-{name.lower()}-{uuid.uuid4().hex}"
        gowa_device_ids.append(device_id)
        if name == "First":
            first_add_started.set()
            await release_first_add.wait()
        return {"id": device_id}

    async def list_devices():
        return [{"id": device_id} for device_id in gowa_device_ids]

    async def remove_device(device_id):
        removed_device_ids.append(device_id)
        return True

    async with (
        _session_factory() as first_db,
        _session_factory() as second_db,
        _session_factory() as cleanup_db,
    ):
        with (
            patch.object(
                whatsapp_service.gowa_client,
                "health_check",
                new=AsyncMock(return_value=True),
            ),
            patch.object(
                whatsapp_service.gowa_client,
                "add_device",
                new=AsyncMock(side_effect=add_device),
            ),
            patch.object(
                whatsapp_service.gowa_client,
                "list_devices",
                new=AsyncMock(side_effect=list_devices),
            ),
            patch.object(
                whatsapp_service.gowa_client,
                "login_device_qr",
                new=AsyncMock(return_value={"code": "SUCCESS", "results": {}}),
            ),
            patch.object(
                whatsapp_service,
                "_force_remove_device_from_gowa",
                new=AsyncMock(side_effect=remove_device),
            ),
        ):
            first_create = asyncio.create_task(
                whatsapp_service.create_device(first_db, "first-user", "First")
            )
            await first_add_started.wait()

            second_create = asyncio.create_task(
                whatsapp_service.create_device(second_db, "second-user", "Second")
            )

            async def cleanup_and_release_lock():
                try:
                    return await whatsapp_service._cleanup_orphaned_devices(cleanup_db)
                finally:
                    await cleanup_db.rollback()

            cleanup = asyncio.create_task(cleanup_and_release_lock())
            await asyncio.sleep(0.05)
            release_first_add.set()

            await asyncio.gather(first_create, second_create, cleanup)

    assert len(gowa_device_ids) == 2
    assert removed_device_ids == []


async def test_delete_device_waits_for_in_flight_create_global_lock(_session_factory):
    """Authorized deletion and creation serialize access to shared GOWA state."""
    owned_device_id = f"delete-vs-create-owned-{uuid.uuid4().hex}"
    created_device_id = f"delete-vs-create-new-{uuid.uuid4().hex}"
    add_started = asyncio.Event()
    release_add = asyncio.Event()

    async def add_device(name: str):
        add_started.set()
        await release_add.wait()
        return {"id": created_device_id}

    async with _session_factory() as setup_db:
        setup_db.add(WhatsAppDeviceDB(user_id=TEST_USER_ID, device_id=owned_device_id))
        await setup_db.commit()

    async with _session_factory() as create_db, _session_factory() as delete_db:
        with (
            patch.object(
                whatsapp_service.gowa_client,
                "health_check",
                new=AsyncMock(return_value=True),
            ),
            patch.object(
                whatsapp_service.gowa_client,
                "add_device",
                new=AsyncMock(side_effect=add_device),
            ),
            patch.object(
                whatsapp_service.gowa_client,
                "list_devices",
                new=AsyncMock(return_value=[{"id": owned_device_id}]),
            ),
            patch.object(
                whatsapp_service.gowa_client,
                "login_device_qr",
                new=AsyncMock(return_value={"code": "SUCCESS", "results": {}}),
            ),
            patch.object(
                whatsapp_service,
                "_force_remove_device_from_gowa",
                new=AsyncMock(return_value=True),
            ) as remove_device,
        ):
            create = asyncio.create_task(
                whatsapp_service.create_device(create_db, "creating-user", "New")
            )
            await add_started.wait()

            delete = asyncio.create_task(
                whatsapp_service.delete_device(delete_db, owned_device_id, TEST_USER_ID)
            )
            await asyncio.sleep(0.05)

            assert not delete.done()
            remove_device.assert_not_awaited()

            release_add.set()
            _, deleted = await asyncio.gather(create, delete)

    assert deleted is True
    remove_device.assert_awaited_once_with(owned_device_id)


async def test_committed_database_state_does_not_leak_to_next_test(db_session):
    """Regression setup: application code is allowed to commit during a test."""
    db_session.add(
        WhatsAppDeviceDB(
            user_id=TEST_USER_ID,
            device_id=ORDER_ISOLATION_DEVICE_ID,
            name="Order isolation regression",
        )
    )
    await db_session.commit()


async def test_database_is_clean_after_test_that_commits(db_session):
    """A committed row from the previous test must not survive fixture teardown."""
    result = await db_session.execute(
        select(WhatsAppDeviceDB).where(
            WhatsAppDeviceDB.device_id == ORDER_ISOLATION_DEVICE_ID
        )
    )
    assert result.scalar_one_or_none() is None


async def test_malformed_api_key_without_origin_returns_auth_error_not_500(unauthed_client):
    response = await unauthed_client.post(
        "/whatsapp/devices/not-a-device/send",
        headers={"X-API-Key": "not-a-valid-api-key"},
        json={"phone": "573001234567", "message": "hello"},
    )

    assert response.status_code == 401
    assert response.status_code != 500
