"""WhatsApp service layer using GOWA v8 multi-device API."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_assistant.service import (
    AUDIO_MESSAGE_TYPES,
    transcribe_audio,
    transcribe_audio_via_service,
)
from app.modules.whatsapp.models import (
    DeviceResponse,
    MessageResponse,
    QRCodeResponse,
    SendMessageResponse,
    WhatsAppDeviceDB,
    WhatsAppMessageDB,
)
from app.modules.whatsapp.whatsapp_client import get_gowa_client

logger = logging.getLogger(__name__)

# Get the singleton GOWA client
gowa_client = get_gowa_client()

# Simple in-memory cache with TTL
_device_cache: Dict[str, Tuple[List[Dict[Any, Any]], datetime]] = {}
_CACHE_TTL_SECONDS = 5  # Cache GOWA device list for 5 seconds

# Cache for individual device status
_device_status_cache: Dict[str, Tuple[Dict[str, Any], datetime]] = {}
_STATUS_CACHE_TTL_SECONDS = 3  # Cache device status for 3 seconds

# GOWA is shared by every tenant. Operations that compare its device list with
# PostgreSQL or add a device must use this transaction-scoped global lock.
_GOWA_ADVISORY_LOCK_KEY = "openwahi:gowa:devices"


async def _acquire_global_gowa_lock(db: AsyncSession) -> None:
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
        {"lock_key": _GOWA_ADVISORY_LOCK_KEY},
    )


# ==================== Device Management ====================


async def create_device(
    db: AsyncSession, user_id: str, name: Optional[str] = None
) -> Tuple[DeviceResponse, QRCodeResponse]:
    """
    Create a new WhatsApp device and start the linking process.

    Uses GOWA v8 multi-device API - single server instance can handle multiple devices.

    Args:
        db: Database session
        user_id: User who owns this device
        name: Optional friendly name for the device

    Returns:
        Tuple of (DeviceResponse, QRCodeResponse)
    """
    # Check if GOWA server is reachable
    is_healthy = await gowa_client.health_check()
    if not is_healthy:
        logger.error("GOWA server is not reachable")
        dummy_device = WhatsAppDeviceDB(
            id=uuid.uuid4(),
            user_id=user_id,
            device_id="error",
            instance_port=3000,
            name=name,
            status="error",
        )
        return DeviceResponse.model_validate(dummy_device), QRCodeResponse(
            device_id="error",
            qr_code=None,
            status="error",
            message="Cannot connect to WhatsApp service. Make sure the GOWA server is running.",
        )

    try:
        # Keep the global lock through cleanup, GOWA creation, and the DB
        # commit so cleanup can never observe an unpersisted GOWA device.
        await _acquire_global_gowa_lock(db)

        # Clean up orphaned devices in GOWA before creating new one
        logger.info(f"Cleaning up orphaned devices before creating new one for user {user_id}")
        await _cleanup_orphaned_devices(db, acquire_lock=False)

        # Add a new device using v8 API
        logger.info(f"Creating new device for user {user_id} with name: {name}")
        add_result = await gowa_client.add_device(name=name)

        # v8 returns: {"id": "uuid", "jid": "", "state": "disconnected"}
        # The 'id' field is used as device_id
        device_id = add_result.get("id") or add_result.get("device_id")

        if not device_id:
            logger.error(f"No device_id or id returned from GOWA: {add_result}")
            raise ValueError("GOWA did not return a device_id")

        logger.info(f"Device created in GOWA with device_id: {device_id}")

        # Create device in database
        db_device = WhatsAppDeviceDB(
            user_id=user_id,
            device_id=device_id,
            instance_port=3000,  # v8 uses single instance
            name=name,
            status="pending",
        )
        db.add(db_device)
        await db.commit()
        await db.refresh(db_device)

        # Get QR code for the new device
        try:
            qr_data = await gowa_client.login_device_qr(device_id)

            # Check if already logged in
            if qr_data.get("code") == "ALREADY_LOGGED_IN":
                db_device.status = "connected"
                db_device.connected_at = datetime.utcnow()
                await db.commit()
                await db.refresh(db_device)

                return DeviceResponse.model_validate(db_device), QRCodeResponse(
                    device_id=device_id,
                    qr_code=None,
                    status="connected",
                    message="Device already connected",
                )

            # v8 returns: {"code":"SUCCESS","results":{"qr_link":"http://..."}}
            results = qr_data.get("results", {})
            qr_link = results.get("qr_link") or qr_data.get("qr_link")

            # Download QR and convert to base64
            qr_base64 = None
            if qr_link:
                qr_base64 = await gowa_client.download_qr_as_base64(qr_link)

            qr_response = QRCodeResponse(
                device_id=device_id,
                qr_code=qr_base64,
                status="pending",
                message="Scan QR code with WhatsApp",
            )
        except Exception as e:
            logger.error(f"Error getting QR code: {e}")
            qr_response = QRCodeResponse(
                device_id=device_id, qr_code=None, status="error", message=str(e)
            )

        device_response = DeviceResponse.model_validate(db_device)
        return device_response, qr_response

    except Exception as e:
        logger.error(f"Error creating device: {e}")
        await db.rollback()

        # Return error response
        dummy_device = WhatsAppDeviceDB(
            id=uuid.uuid4(),
            user_id=user_id,
            device_id="error",
            instance_port=3000,
            name=name,
            status="error",
        )
        return DeviceResponse.model_validate(dummy_device), QRCodeResponse(
            device_id="error",
            qr_code=None,
            status="error",
            message=f"Error creating device: {str(e)}",
        )


async def get_devices(db: AsyncSession, user_id: str) -> List[DeviceResponse]:
    """
    Get all devices for a user, syncing with GOWA v8 API.
    Uses caching to reduce API calls and improve performance.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        List of DeviceResponse
    """
    try:
        # Check cache first
        cache_key = "gowa_devices"
        now = datetime.utcnow()

        if cache_key in _device_cache:
            cached_devices, cached_at = _device_cache[cache_key]
            if now - cached_at < timedelta(seconds=_CACHE_TTL_SECONDS):
                gowa_devices = cached_devices
                logger.debug("Using cached GOWA devices")
            else:
                # Cache expired, fetch new data
                gowa_devices = await gowa_client.list_devices()
                _device_cache[cache_key] = (gowa_devices, now)
        else:
            # No cache, fetch data
            gowa_devices = await gowa_client.list_devices()
            _device_cache[cache_key] = (gowa_devices, now)

        # Create a map of device_id -> GOWA device info
        gowa_device_map = {}
        for device in gowa_devices:
            device_id = device.get("device_id") or device.get("id")
            if device_id:
                gowa_device_map[device_id] = device

        # Get devices from database for this user
        result = await db.execute(
            select(WhatsAppDeviceDB)
            .where(WhatsAppDeviceDB.user_id == user_id)
            .order_by(WhatsAppDeviceDB.created_at.desc())
        )
        db_devices = result.scalars().all()

        # Get all device_ids from our database (for cleanup)
        {db_device.device_id for db_device in db_devices}

        # Note: Orphan cleanup moved to background task to improve performance
        # Cleanup runs via /whatsapp/devices/cleanup endpoint

        # Sync status from GOWA
        updated_devices = []
        for db_device in db_devices:
            gowa_device = gowa_device_map.get(db_device.device_id)

            if gowa_device:
                # Update status from GOWA v8 (uses 'state' field)
                gowa_status = gowa_device.get("state") or gowa_device.get("status", "unknown")

                # Check if device has JID (only set after QR is scanned)
                jid = gowa_device.get("jid") or gowa_device.get("phone")

                # Map GOWA status to our status
                # IMPORTANT: Only mark as connected if JID exists (QR was actually scanned)
                # GOWA v8 uses "logged_in" state when device is connected
                if gowa_status in ["connected", "authenticated", "logged_in"] and jid:
                    db_device.status = "connected"
                    if not db_device.connected_at:
                        db_device.connected_at = datetime.utcnow()
                elif gowa_status in ["disconnected", "logged_out"]:
                    db_device.status = "disconnected"
                elif gowa_status in ["pending", "qr_generated"] or (
                    gowa_status == "connected" and not jid
                ):
                    # If GOWA says connected but no JID, it's actually pending
                    db_device.status = "pending"

                # Update phone if available
                phone = gowa_device.get("phone")
                if phone and not db_device.phone:
                    db_device.phone = phone

                # Update name if available
                device_name = gowa_device.get("name")
                if device_name and not db_device.name:
                    db_device.name = device_name

            else:
                # Device not found in GOWA, mark as disconnected
                if db_device.status != "disconnected":
                    db_device.status = "disconnected"

            updated_devices.append(db_device)

        await db.commit()

        # Convert to response models
        return [DeviceResponse.model_validate(d) for d in updated_devices]

    except Exception as e:
        logger.error(f"Error getting devices: {e}")
        # Return devices from DB only
        result = await db.execute(
            select(WhatsAppDeviceDB)
            .where(WhatsAppDeviceDB.user_id == user_id)
            .order_by(WhatsAppDeviceDB.created_at.desc())
        )
        db_devices = result.scalars().all()
        return [DeviceResponse.model_validate(d) for d in db_devices]


async def get_device(db: AsyncSession, device_id: str, user_id: str) -> Optional[DeviceResponse]:
    """
    Get a specific device by UUID (DB id) or GOWA device_id.
    """
    # Try UUID first
    try:
        result = await db.execute(
            select(WhatsAppDeviceDB)
            .where(WhatsAppDeviceDB.id == uuid.UUID(device_id))
            .where(WhatsAppDeviceDB.user_id == user_id)
        )
        db_device = result.scalar_one_or_none()
    except (ValueError, AttributeError):
        db_device = None

    # If not found, try GOWA device_id
    if not db_device:
        result = await db.execute(
            select(WhatsAppDeviceDB)
            .where(WhatsAppDeviceDB.device_id == device_id)
            .where(WhatsAppDeviceDB.user_id == user_id)
        )
        db_device = result.scalar_one_or_none()

    if not db_device:
        return None

    return DeviceResponse.model_validate(db_device)


async def delete_device(db: AsyncSession, device_id: str, user_id: str) -> bool:
    """
    Delete/unlink a device from both DB and GOWA v8.
    Ensures complete removal including logout and session cleanup.

    Args:
        db: Database session
        device_id: Device ID (can be UUID from DB or GOWA device_id)
        user_id: User ID (for authorization)

    Returns:
        True if deleted, False if not found
    """
    # Get from database - try both UUID and device_id
    try:
        result = await db.execute(
            select(WhatsAppDeviceDB)
            .where(WhatsAppDeviceDB.id == uuid.UUID(device_id))
            .where(WhatsAppDeviceDB.user_id == user_id)
        )
        db_device = result.scalar_one_or_none()
    except (ValueError, AttributeError):
        db_device = None

    # If not found by UUID, try by GOWA device_id
    if not db_device:
        result = await db.execute(
            select(WhatsAppDeviceDB)
            .where(WhatsAppDeviceDB.device_id == device_id)
            .where(WhatsAppDeviceDB.user_id == user_id)
        )
        db_device = result.scalar_one_or_none()

    if not db_device:
        # User-scoped deletion must never clean up global GOWA orphans. A missing
        # row may belong to another tenant; orphan cleanup is admin-only.
        return False

    # Serialize authorized removals with device creation and admin orphan cleanup.
    # Keep the transaction-scoped lock through both the GOWA operation and DB commit.
    await _acquire_global_gowa_lock(db)

    # Complete removal from GOWA v8 using GOWA device_id
    await _force_remove_device_from_gowa(db_device.device_id)

    # Delete from database
    await db.delete(db_device)
    await db.commit()

    logger.info(f"Device {db_device.device_id} completely removed from both GOWA and database")

    return True


async def get_device_qr(db: AsyncSession, device_id: str, user_id: str) -> Optional[QRCodeResponse]:
    """
    Get QR code for a device (for re-scanning if needed).
    Cached to reduce repeated calls during QR refresh.

    Args:
        db: Database session
        device_id: Device ID
        user_id: User ID (for authorization)

    Returns:
        QRCodeResponse or None if device not found
    """
    # Verify device exists and belongs to user
    device = await get_device(db, device_id, user_id)
    if not device:
        return None

    # Get QR from GOWA using GOWA device_id
    try:
        qr_data = await gowa_client.login_device_qr(device.device_id)

        # Check if already logged in
        if qr_data.get("code") == "ALREADY_LOGGED_IN":
            return QRCodeResponse(
                device_id=device.device_id,
                qr_code=None,
                status="connected",
                message="Device already connected",
            )

        # Get QR link
        results = qr_data.get("results", {})
        qr_link = results.get("qr_link") or qr_data.get("qr_link")

        # Download and convert to base64
        qr_base64 = None
        if qr_link:
            qr_base64 = await gowa_client.download_qr_as_base64(qr_link)

        return QRCodeResponse(
            device_id=device.device_id,
            qr_code=qr_base64,
            status="pending",
            message="Scan QR code with WhatsApp",
        )

    except Exception as e:
        logger.error(f"Error getting QR for device {device.device_id}: {e}")
        return QRCodeResponse(
            device_id=device.device_id, qr_code=None, status="error", message=str(e)
        )


# ==================== Message Operations ====================


async def send_message(
    db: AsyncSession, device_id: str, user_id: str, phone: str, message: str
) -> SendMessageResponse:
    """
    Send a WhatsApp message using a specific device.

    Args:
        db: Database session
        device_id: Device to send from
        user_id: User ID (for authorization)
        phone: Recipient phone number
        message: Message text

    Returns:
        SendMessageResponse
    """
    # Verify device exists and belongs to user
    device = await get_device(db, device_id, user_id)
    if not device:
        return SendMessageResponse(success=False, error="Device not found")

    if device.status != "connected":
        return SendMessageResponse(
            success=False, error=f"Device is not connected (status: {device.status})"
        )

    try:
        # Send via GOWA v8 API (use device.device_id which is the GOWA internal ID)
        result = await gowa_client.send_message(device.device_id, phone, message)

        # v8 returns: {"code":"SUCCESS","results":{"message_id":"..."}}
        if result.get("code") == "SUCCESS":
            results = result.get("results", {})
            message_id = results.get("message_id") or results.get("id")

            # Save to database
            db_message = WhatsAppMessageDB(
                device_id=device.id,
                message_id=message_id or f"msg_{uuid.uuid4().hex[:12]}",
                from_phone=device.phone or device.device_id,
                to_phone=phone,
                body=message,
                message_type="text",
                is_from_me=True,
                status="sent",
                timestamp=datetime.utcnow(),
            )
            db.add(db_message)
            await db.commit()

            return SendMessageResponse(success=True, message_id=message_id)
        else:
            error_msg = result.get("message", "Unknown error")
            return SendMessageResponse(success=False, error=error_msg)

    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return SendMessageResponse(success=False, error=str(e))


async def get_messages(
    db: AsyncSession, device_id: str, user_id: str, limit: int = 50, offset: int = 0
) -> Tuple[List[MessageResponse], int]:
    """
    Get messages for a device.

    Args:
        db: Database session
        device_id: Device ID
        user_id: User ID (for authorization)
        limit: Max messages to return
        offset: Pagination offset

    Returns:
        Tuple of (messages, total_count)
    """
    # Verify device exists and belongs to user
    device = await get_device(db, device_id, user_id)
    if not device:
        return [], 0

    # Get messages from database
    result = await db.execute(
        select(WhatsAppMessageDB)
        .where(WhatsAppMessageDB.device_id == device.id)
        .order_by(WhatsAppMessageDB.timestamp.desc())
        .limit(limit)
        .offset(offset)
    )
    messages = result.scalars().all()

    # Get total count
    count_result = await db.execute(
        select(WhatsAppMessageDB).where(WhatsAppMessageDB.device_id == device.id)
    )
    total = len(count_result.scalars().all())

    return [MessageResponse.model_validate(m) for m in messages], total


async def get_chats(db: AsyncSession, user_id: str, device_id: Optional[str] = None) -> List[Any]:
    """
    Get all chats (conversations grouped by phone number) for a user.

    Args:
        db: Database session
        user_id: User ID
        device_id: Optional device ID to filter chats

    Returns:
        List of ChatSummary objects
    """
    from sqlalchemy import case, desc, func

    from app.modules.whatsapp.models import ChatSummary

    # Build base query - get user's devices
    device_query = select(WhatsAppDeviceDB).where(WhatsAppDeviceDB.user_id == user_id)

    # Filter by specific device if provided
    if device_id:
        try:
            device_query = device_query.where(WhatsAppDeviceDB.id == uuid.UUID(device_id))
        except ValueError:
            # Try by GOWA device_id
            device_query = device_query.where(WhatsAppDeviceDB.device_id == device_id)

    result = await db.execute(device_query)
    devices = result.scalars().all()

    if not devices:
        return []

    device_ids = [d.id for d in devices]

    # Create a map of device_id -> device for quick lookup
    device_map = {str(d.id): d for d in devices}

    # Query to get chat summaries
    # Group messages by the "other" phone (not the device's phone)
    # For each group, get last message, count, etc.
    chat_query = (
        select(
            WhatsAppMessageDB.device_id,
            # The "other" phone is from_phone if not from me, else to_phone
            case(
                (WhatsAppMessageDB.is_from_me == False, WhatsAppMessageDB.from_phone),
                else_=WhatsAppMessageDB.to_phone,
            ).label("chat_phone"),
            func.max(WhatsAppMessageDB.timestamp).label("last_timestamp"),
            func.count(WhatsAppMessageDB.id).label("message_count"),
        )
        .where(WhatsAppMessageDB.device_id.in_(device_ids))
        .group_by(WhatsAppMessageDB.device_id, "chat_phone")
        .order_by(desc("last_timestamp"))
    )

    result = await db.execute(chat_query)
    chat_groups = result.all()

    chats = []
    for group in chat_groups:
        device_id_uuid = group.device_id
        chat_phone = group.chat_phone

        # Get the last message for this chat
        last_msg_query = (
            select(WhatsAppMessageDB)
            .where(WhatsAppMessageDB.device_id == device_id_uuid)
            .where(
                (
                    (WhatsAppMessageDB.is_from_me == False)
                    & (WhatsAppMessageDB.from_phone == chat_phone)
                )
                | (
                    (WhatsAppMessageDB.is_from_me == True)
                    & (WhatsAppMessageDB.to_phone == chat_phone)
                )
            )
            .order_by(WhatsAppMessageDB.timestamp.desc())
            .limit(1)
        )

        last_msg_result = await db.execute(last_msg_query)
        last_msg = last_msg_result.scalar_one_or_none()

        if last_msg:
            device = device_map.get(str(device_id_uuid))
            chat_summary = {
                "phone": chat_phone,
                "device_id": str(device_id_uuid),
                "device_phone": device.phone if device else None,
                "last_message": last_msg.body or f"[{last_msg.message_type}]",
                "last_message_timestamp": last_msg.timestamp.isoformat()
                if last_msg.timestamp
                else None,
                "total_messages": group.message_count,
                "is_last_from_me": last_msg.is_from_me,
                "unread_count": 0,  # TODO: Implement unread tracking
            }
            chats.append(chat_summary)

    return chats


# ==================== Webhook Processing ====================


async def process_webhook(
    db: AsyncSession,
    webhook_type: str,
    device_id: Optional[str],
    data: dict,
    instance_port: Optional[int] = None,
    ws_manager=None,
):
    """
    Process incoming webhook from GOWA v8.

    v8 webhooks include device_id in the top-level payload:
    {
      "event": "message",
      "device_id": "628123456789@s.whatsapp.net",
      "payload": { ... }
    }

    Args:
        db: Database session
        webhook_type: Type of webhook event
        device_id: Device that received the event
        data: Webhook payload data
        instance_port: (Deprecated in v8, kept for backwards compatibility)
        ws_manager: WebSocket manager for broadcasting events (optional)
    """
    logger.info(
        f"Processing webhook: type={webhook_type}, device_id={device_id}, data_keys={list(data.keys())}"
    )

    if not device_id:
        logger.warning(f"Webhook received without device_id: {data}")
        return

    # Find device in database
    # Try by GOWA device_id first (UUID format)
    result = await db.execute(
        select(WhatsAppDeviceDB).where(WhatsAppDeviceDB.device_id == device_id)
    )
    db_device = result.scalar_one_or_none()

    # If not found, try by phone/JID (WhatsApp format like 15551234567@s.whatsapp.net)
    if not db_device:
        # Extract phone number from JID
        phone_number = device_id.replace("@s.whatsapp.net", "").replace("@c.us", "")
        result = await db.execute(
            select(WhatsAppDeviceDB).where(WhatsAppDeviceDB.phone == phone_number)
        )
        db_device = result.scalar_one_or_none()

    if not db_device:
        logger.warning(
            f"Device {device_id} not found in database (tried GOWA ID and phone lookup), ignoring webhook"
        )
        return

    # Process based on webhook type
    if webhook_type == "message":
        await _process_message_webhook(db, db_device, data, ws_manager)
    elif webhook_type == "message.ack":
        await _process_message_ack_webhook(db, db_device, data, ws_manager)
    elif webhook_type in ["connection", "state"]:
        # Both 'connection' and 'state' events indicate status changes
        await _process_connection_webhook(db, db_device, data, ws_manager)
    else:
        logger.info(f"Unhandled webhook type: {webhook_type}")


async def _process_message_webhook(
    db: AsyncSession, device: WhatsAppDeviceDB, data: dict, ws_manager=None
):
    """Process incoming message webhook and broadcast via WebSocket."""
    try:
        message_id = data.get("message_id") or data.get("id")
        # Clean phone numbers - remove JID suffix if present
        from_phone_raw = data.get("from", "")
        from_phone = from_phone_raw.replace("@s.whatsapp.net", "").replace("@c.us", "")
        to_phone_raw = data.get("to", device.phone or device.device_id)
        to_phone = (
            to_phone_raw.replace("@s.whatsapp.net", "").replace("@c.us", "") if to_phone_raw else ""
        )
        body = data.get("body") or data.get("message") or data.get("text", "")
        timestamp_str = data.get("timestamp")
        is_from_me = data.get("is_from_me", False) or data.get("fromMe", False)

        # ------------------------------------------------------------------
        # Detect message type and media URL from GOWA v8 payload.
        #
        # GOWA does NOT always send a "type" field — instead it uses dedicated keys:
        #   text     → "body" key present, no media keys
        #   audio    → "audio" key  (value: "statics/media/file.ogg; codecs=opus")
        #   image    → "image" key
        #   video    → "video" key
        #   document → "document" key
        #
        # For audio the value includes codec metadata after a semicolon which
        # must be stripped before building the download URL.
        # ------------------------------------------------------------------
        audio_raw = data.get("audio") or data.get("ptt") or data.get("voice")
        image_raw = data.get("image")
        video_raw = data.get("video")
        document_raw = data.get("document")

        if audio_raw:
            message_type = "audio"
            # Strip codec suffix: "statics/media/file.ogg; codecs=opus" → "statics/media/file.ogg"
            audio_path = audio_raw.strip()  # Keep full filename including codec suffix (e.g. ".ogg; codecs=opus")
            media_url = f"{gowa_client.base_url}/{audio_path}"
        elif image_raw:
            message_type = "image"
            media_url = (
                image_raw if image_raw.startswith("http") else f"{gowa_client.base_url}/{image_raw}"
            )
        elif video_raw:
            message_type = "video"
            media_url = (
                video_raw if video_raw.startswith("http") else f"{gowa_client.base_url}/{video_raw}"
            )
        elif document_raw:
            message_type = "document"
            media_url = (
                document_raw
                if document_raw.startswith("http")
                else f"{gowa_client.base_url}/{document_raw}"
            )
        else:
            message_type = data.get("type", "text")
            media_url = data.get("media_url") or data.get("mediaUrl") or data.get("url") or None

        # Parse timestamp
        timestamp = datetime.utcnow()
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except Exception:
                pass

        # Check if message already exists
        existing = await db.execute(
            select(WhatsAppMessageDB).where(WhatsAppMessageDB.message_id == message_id)
        )
        if existing.scalar_one_or_none():
            logger.debug(f"Message {message_id} already exists, skipping")
            return

        # Create message record
        db_message = WhatsAppMessageDB(
            device_id=device.id,
            message_id=message_id,
            from_phone=from_phone,
            to_phone=to_phone,
            body=body,
            message_type=message_type,
            is_from_me=is_from_me,
            status="received",
            media_url=media_url,
            timestamp=timestamp,
        )
        db.add(db_message)
        await db.commit()
        await db.refresh(db_message)

        logger.info(f"Saved message {message_id} from webhook")

        # 🔗 WEBHOOK FORWARDING - Forward incoming message to user's configured webhook
        if not is_from_me:
            try:
                from app.modules.developer.service import DeveloperService

                webhook_data = {
                    "message_id": str(db_message.id),
                    "whatsapp_message_id": message_id,
                    "device_id": str(device.id),
                    "from_phone": from_phone,
                    "to_phone": to_phone,
                    "body": body,
                    "message_type": message_type,
                    "timestamp": timestamp.isoformat(),
                }

                await DeveloperService.trigger_webhook(
                    db=db,
                    user_id=str(device.user_id),
                    event="message.received",
                    data=webhook_data,
                )
            except Exception as webhook_error:
                logger.warning(f"Failed to trigger user webhook: {webhook_error}")

        # ✨ AI ASSISTANT INTEGRATION - Process incoming messages with AI
        # Handles text messages directly; audio/ptt messages are transcribed first.

        is_audio = message_type in AUDIO_MESSAGE_TYPES
        should_process_ai = not is_from_me and (
            (message_type == "text" and body) or (is_audio and media_url)
        )

        if should_process_ai and is_audio and media_url:
            logger.info(
                f"Audio message received from {from_phone}, attempting transcription..."
            )
            try:
                from sqlalchemy import select as sa_select

                from app.modules.ai_assistant.encryption import decrypt_api_key
                from app.modules.ai_assistant.models import WhatsAppAIConfigDB

                ai_config_result = await db.execute(
                    sa_select(WhatsAppAIConfigDB).where(
                        WhatsAppAIConfigDB.device_id == device.id,
                        WhatsAppAIConfigDB.is_enabled == True,
                    )
                )
                ai_config = ai_config_result.scalar_one_or_none()

                if ai_config:
                    user_api_key = decrypt_api_key(ai_config.api_key_encrypted)
                    audio_bytes = await gowa_client.download_media(media_url)

                    # Intentar microservicio primero
                    transcribed_text = await transcribe_audio_via_service(
                        audio_bytes=audio_bytes,
                        filename="audio.ogg",
                    )

                    # Fallback a Groq/managed-key si el microservicio no está disponible
                    if transcribed_text is None:
                        transcribed_text = await transcribe_audio(
                            audio_bytes=audio_bytes,
                            api_key=user_api_key,
                            provider=ai_config.provider,
                        )

                    if transcribed_text:
                        body = transcribed_text
                        db_message.body = transcribed_text
                        db_message.message_type = "audio_transcribed"
                        await db.commit()
                        await db.refresh(db_message)
                        logger.info(
                            f"Audio transcribed for {from_phone}: '{transcribed_text[:80]}...'"
                        )
                    else:
                        logger.warning(
                            f"Transcription returned empty for message from {from_phone}, skipping AI"
                        )
                        should_process_ai = False
                else:
                    logger.info(
                        f"No active AI config for device {device.id}, skipping audio transcription"
                    )
                    should_process_ai = False

            except Exception as transcription_error:
                logger.error(
                    f"Error during audio transcription for {from_phone}: {transcription_error}",
                    exc_info=True,
                )
                # Fallback: if audio download/transcription fails, still process with AI
                # so the user gets a response asking them to type their message instead.
                logger.warning(
                    f"Audio download/transcription failed for {from_phone}, using fallback text"
                )
                body = "[El usuario envió un mensaje de voz que no pudo ser procesado. Responde amablemente indicando que no pudiste escuchar el audio y pídele que escriba su mensaje.]"
                should_process_ai = True

        if should_process_ai:
            logger.info(f"Processing message for AI Assistant: from={from_phone}")
            try:
                from app.modules.ai_assistant.service import AIAssistantService

                # 🔄 Send typing indicator to show bot is processing
                logger.info(f"Sending typing indicator to {from_phone}...")
                try:
                    await gowa_client.send_typing_indicator(
                        device_id=device.device_id, phone=from_phone, start=True
                    )
                except Exception as typing_error:
                    logger.warning(f"Failed to send typing indicator: {typing_error}")

                ai_response = await AIAssistantService.process_incoming_message(
                    db=db,
                    device_id=device.id,
                    from_phone=from_phone,
                    message_text=body,
                    message_id=db_message.id,
                )

                if ai_response:
                    logger.info(f"AI generated response for {from_phone}, sending...")
                    logger.info(f"Sending to device_id={device.device_id}, phone={from_phone}")
                    logger.info(f"Response preview: {ai_response[:100]}...")

                    # Format response for WhatsApp
                    from app.modules.whatsapp.formatter import clean_markdown_for_whatsapp

                    formatted_response = clean_markdown_for_whatsapp(ai_response)

                    # Send AI response back via WhatsApp
                    send_result = await gowa_client.send_message(
                        device_id=device.device_id,
                        phone=from_phone,
                        message=formatted_response,
                    )

                    logger.info(f"Send result from GOWA: {send_result}")

                    # Check if send was successful
                    # GOWA v8 returns {"code": "SUCCESS", "results": {...}}
                    # Older versions may return {"status": "success"} or {"success": true}
                    is_success = (
                        send_result.get("success") is True
                        or send_result.get("status") == "success"
                        or send_result.get("code") == "SUCCESS"
                    )

                    if is_success:
                        logger.info(f"AI response sent successfully to {from_phone}")

                        # 🔄 Stop typing indicator after message sent
                        try:
                            await gowa_client.send_typing_indicator(
                                device_id=device.device_id,
                                phone=from_phone,
                                start=False,
                            )
                        except Exception as typing_error:
                            logger.warning(f"Failed to stop typing indicator: {typing_error}")

                        # Save AI response as a sent message
                        # Use device.phone if available, otherwise use to_phone from original message
                        bot_phone = device.phone if device.phone else to_phone

                        # Extract message_id from GOWA v8 response
                        # v8: {"code": "SUCCESS", "results": {"message_id": "..."}}
                        results = send_result.get("results", {})
                        msg_id = (
                            results.get("message_id")
                            or send_result.get("message_id")
                            or f"ai_{uuid.uuid4()}"
                        )

                        ai_message = WhatsAppMessageDB(
                            device_id=device.id,
                            message_id=msg_id,
                            from_phone=bot_phone,
                            to_phone=from_phone,
                            body=formatted_response,
                            message_type="text",
                            is_from_me=True,
                            status="sent",
                            timestamp=datetime.utcnow(),
                        )
                        db.add(ai_message)
                        await db.commit()
                        await db.refresh(ai_message)

                        logger.info(
                            f"Saved AI message {ai_message.message_id} to database: "
                            f"from={bot_phone} to={from_phone}"
                        )

                        # Broadcast AI response via WebSocket
                        if ws_manager:
                            logger.info(
                                f"Broadcasting AI message via WebSocket to device {device.id}"
                            )
                            await ws_manager.broadcast_message_event(
                                str(device.id),
                                "new_message",  # Use same event as regular messages
                                {
                                    "id": str(ai_message.id),
                                    "message_id": ai_message.message_id,
                                    "from": bot_phone,
                                    "from_phone": bot_phone,
                                    "to": from_phone,
                                    "to_phone": from_phone,
                                    "body": formatted_response,
                                    "type": "text",
                                    "message_type": "text",
                                    "is_from_me": True,
                                    "status": "sent",
                                    "timestamp": ai_message.timestamp.isoformat(),
                                    "created_at": ai_message.created_at.isoformat()
                                    if ai_message.created_at
                                    else ai_message.timestamp.isoformat(),
                                },
                            )
                            logger.info(
                                f"WebSocket broadcast completed for AI message to {from_phone}"
                            )
                    else:
                        logger.error(f"Failed to send AI response. Full result: {send_result}")
                        logger.error(
                            f"Error from GOWA: {send_result.get('error') or send_result.get('message') or 'Unknown error'}"
                        )

                        # 🔄 Stop typing indicator on error
                        try:
                            await gowa_client.send_typing_indicator(
                                device_id=device.device_id,
                                phone=from_phone,
                                start=False,
                            )
                        except Exception as typing_error:
                            logger.warning(
                                f"Failed to stop typing indicator after error: {typing_error}"
                            )
                else:
                    logger.debug(f"No AI response generated for {from_phone}")

                    # 🔄 Stop typing indicator if no response generated
                    try:
                        await gowa_client.send_typing_indicator(
                            device_id=device.device_id, phone=from_phone, start=False
                        )
                    except Exception as typing_error:
                        logger.warning(f"Failed to stop typing indicator: {typing_error}")

            except Exception as ai_error:
                logger.error(f"Error in AI Assistant processing: {ai_error}", exc_info=True)

                # 🔄 Stop typing indicator on exception
                try:
                    await gowa_client.send_typing_indicator(
                        device_id=device.device_id, phone=from_phone, start=False
                    )
                except Exception as typing_error:
                    logger.warning(
                        f"Failed to stop typing indicator after exception: {typing_error}"
                    )

                # Don't fail the webhook if AI processing fails

        # Broadcast to WebSocket subscribers
        if ws_manager:
            try:
                # Use the (potentially updated) values from db_message so the frontend
                # receives 'audio_transcribed' type and the transcribed body text.
                await ws_manager.broadcast_message_event(
                    str(device.id),
                    "new_message",
                    {
                        "id": str(db_message.id),
                        "message_id": message_id,
                        "from": from_phone,
                        "from_phone": from_phone,
                        "to": to_phone,
                        "to_phone": to_phone,
                        "body": db_message.body,
                        "type": db_message.message_type,
                        "message_type": db_message.message_type,
                        "is_from_me": False,
                        "status": "received",
                        "timestamp": timestamp.isoformat(),
                    },
                )
                logger.info(
                    f"Broadcasted new_message via WebSocket: "
                    f"from={from_phone}, to={to_phone}, body={body[:50] if body else 'N/A'}"
                )
            except Exception as ws_error:
                logger.error(f"Error broadcasting message via WebSocket: {ws_error}")

    except Exception as e:
        logger.error(f"Error processing message webhook: {e}")
        await db.rollback()


async def _process_message_ack_webhook(
    db: AsyncSession, device: WhatsAppDeviceDB, data: dict, ws_manager=None
):
    """Process message acknowledgment webhook."""
    try:
        message_id = data.get("message_id") or data.get("id")
        ack_level = data.get("ack", 0)

        # Map ack levels: 0=sent, 1=delivered, 2=read
        status_map = {0: "sent", 1: "delivered", 2: "read"}
        new_status = status_map.get(ack_level, "sent")

        # Update message status
        result = await db.execute(
            select(WhatsAppMessageDB)
            .where(WhatsAppMessageDB.message_id == message_id)
            .where(WhatsAppMessageDB.device_id == device.id)
        )
        db_message = result.scalar_one_or_none()

        if db_message:
            db_message.status = new_status
            await db.commit()
            logger.info(f"Updated message {message_id} status to {new_status}")

    except Exception as e:
        logger.error(f"Error processing message ack webhook: {e}")
        await db.rollback()


async def _process_connection_webhook(
    db: AsyncSession, device: WhatsAppDeviceDB, data: dict, ws_manager=None
):
    """Process connection status webhook (handles both 'connection' and 'state' events)."""
    try:
        # v8 uses 'state' field for status
        status = (data.get("state") or data.get("status", "")).lower()

        # Also check for JID to determine if truly connected
        jid = data.get("jid") or data.get("phone")

        logger.info(
            f"Processing connection webhook for device {device.device_id}: "
            f"status={status}, jid={jid}"
        )

        # Update device status based on webhook data
        if status in ["connected", "authenticated", "logged_in"]:
            # Only mark as connected if JID exists (actually authenticated)
            if jid:
                device.status = "connected"
                if not device.connected_at:
                    device.connected_at = datetime.utcnow()

                # Extract and update phone if available
                phone_number = jid.replace("@s.whatsapp.net", "").replace("@c.us", "")
                if phone_number and not device.phone:
                    device.phone = phone_number
                    logger.info(f"Updated device phone to {phone_number}")
            else:
                # Connected but no JID means QR not scanned yet
                device.status = "pending"

        elif status in ["disconnected", "logged_out", "logout"]:
            device.status = "disconnected"

        await db.commit()
        await db.refresh(device)

        logger.info(
            f"Updated device {device.device_id} status to {device.status} (phone: {device.phone})"
        )

        # Clear caches for this device to ensure fresh data on next request
        device_cache_key = str(device.device_id)
        if device_cache_key in _device_status_cache:
            del _device_status_cache[device_cache_key]
            logger.debug(f"Cleared status cache for device {device.device_id}")

        # Clear the devices list cache to force refresh
        if "gowa_devices" in _device_cache:
            del _device_cache["gowa_devices"]
            logger.debug("Cleared devices list cache")

        # Broadcast to WebSocket subscribers - use device.id (UUID) not device_id (GOWA ID)
        if ws_manager:
            try:
                await ws_manager.broadcast_device_status(
                    str(device.id),
                    str(device.status),
                    str(device.phone) if device.phone else None,
                    f"Device {device.status}",
                )
                logger.info(
                    f"Broadcasted device status update via WebSocket: "
                    f"device_id={device.id}, status={device.status}"
                )
            except Exception as ws_error:
                logger.error(f"Error broadcasting device status via WebSocket: {ws_error}")

    except Exception as e:
        logger.error(f"Error processing connection webhook: {e}")
        await db.rollback()


# ==================== Helper Functions ====================


async def _force_remove_device_from_gowa(device_id: str) -> bool:
    """
    Force removal of a device from GOWA with logout first.

    This ensures complete cleanup of device sessions.

    Args:
        device_id: Device ID to remove

    Returns:
        True if removed successfully
    """
    try:
        # First try to logout the device
        try:
            await gowa_client.logout_device(device_id)
            logger.info(f"Device {device_id} logged out from GOWA")
        except Exception as e:
            logger.debug(f"Could not logout device {device_id}: {e}")

        # Then remove the device completely
        await gowa_client.remove_device(device_id)
        logger.info(f"Device {device_id} removed from GOWA")
        return True

    except Exception as e:
        logger.warning(f"Could not remove device {device_id} from GOWA: {e}")
        return False


async def _cleanup_orphaned_devices(db: AsyncSession, *, acquire_lock: bool = True) -> int:
    """
    Clean up devices that exist in GOWA but not in our database.

    This prevents old sessions from being reused when creating new devices.

    Args:
        db: Database session
    Returns:
        Number of orphaned devices cleaned up
    """
    cleanup_count = 0

    try:
        if acquire_lock:
            await _acquire_global_gowa_lock(db)

        # Get all devices from GOWA
        gowa_devices = await gowa_client.list_devices()

        # A GOWA instance is shared by all users, so every registered device must
        # be protected from cleanup regardless of which user triggered it.
        result = await db.execute(select(WhatsAppDeviceDB.device_id))
        db_device_ids = {row[0] for row in result.all()}

        # Find and remove orphaned devices
        for gowa_device in gowa_devices:
            gowa_device_id = gowa_device.get("device_id") or gowa_device.get("id")

            if gowa_device_id and gowa_device_id not in db_device_ids:
                logger.warning(f"Cleaning up orphaned device in GOWA: {gowa_device_id}")
                try:
                    if await _force_remove_device_from_gowa(gowa_device_id):
                        cleanup_count += 1
                except Exception as e:
                    logger.error(f"Failed to cleanup orphaned device {gowa_device_id}: {e}")

        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} orphaned devices from GOWA")

    except Exception as e:
        logger.error(f"Error during orphaned device cleanup: {e}")

    return cleanup_count
