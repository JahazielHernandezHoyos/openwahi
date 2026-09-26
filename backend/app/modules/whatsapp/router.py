"""WhatsApp API router."""

import hashlib
import hmac
import json
import logging
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.config.settings import settings
from app.core.dependencies import get_admin_user, get_current_user_id, get_current_user_id_flexible
from app.core.rate_limit import RateLimits, limiter
from app.modules.subscriptions.service import get_device_limit
from app.modules.whatsapp import service
from app.modules.whatsapp.models import (
    DeviceCreate,
    DeviceListResponse,
    DeviceResponse,
    MessageListResponse,
    QRCodeResponse,
    SendMessageRequest,
    SendMessageResponse,
    WhatsAppDeviceDB,
)
from app.modules.whatsapp.websocket import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

# Global cache dictionaries for improving performance
_qr_cache = {}  # {device_id: (response, timestamp)}
_status_cache = {}  # {device_id: (response, timestamp)}


# ==================== WebSocket Endpoints ====================


@router.websocket("/devices/{device_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    device_id: str,
    token: str = Query(..., description="JWT token for authentication"),
):
    """
    WebSocket endpoint for real-time WhatsApp message updates.

    Connect to this endpoint to receive real-time notifications for:
    - New incoming messages
    - Message status updates (sent, delivered, read)
    - Device connection status changes

    Example client connection:
    ```javascript
    const ws = new WebSocket(`ws://localhost:8000/whatsapp/devices/${deviceId}/ws?token=${jwtToken}`);

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Received:', data);

        switch(data.type) {
            case 'new_message':
                // Handle new message
                break;
            case 'message_ack':
                // Handle message acknowledgment
                break;
            case 'device_status':
                // Handle device status change
                break;
        }
    };
    ```
    """
    # Authenticate user from Firebase ID token
    try:
        from app.core.security import get_user_id_from_token

        user_id = await get_user_id_from_token(token)
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {e}")
        await websocket.close(code=1008, reason="Authentication failed")
        return

    # Verify device belongs to user
    import uuid as uuid_lib

    from sqlalchemy import select

    from app.modules.whatsapp.models import WhatsAppDeviceDB

    db_gen = get_db()
    db = await anext(db_gen)
    try:
        try:
            result = await db.execute(
                select(WhatsAppDeviceDB)
                .where(WhatsAppDeviceDB.id == uuid_lib.UUID(device_id))
                .where(WhatsAppDeviceDB.user_id == user_id)
            )
            db_device = result.scalar_one_or_none()
        except (ValueError, AttributeError):
            db_device = None

        if not db_device:
            await websocket.close(code=1008, reason="Device not found or unauthorized")
            return
    finally:
        await db_gen.aclose()

    # Connect to WebSocket manager
    connected = await ws_manager.connect(websocket, device_id, user_id)
    if not connected:
        logger.error(f"Failed to establish WebSocket connection for device {device_id}")
        return

    try:
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for any message from client (ping/pong, etc.)
                data = await websocket.receive_text()

                # Handle client messages if needed
                try:
                    message = json.loads(data) if isinstance(data, str) else data

                    # Handle ping/pong
                    if message.get("type") == "ping":
                        await ws_manager.send_personal_message(
                            {
                                "type": "pong",
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                            websocket,
                        )
                except Exception:
                    pass  # Ignore malformed messages

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for device {device_id}")
                break
            except Exception as e:
                logger.error(f"WebSocket error for device {device_id}: {e}")
                break

    finally:
        ws_manager.disconnect(websocket, device_id, user_id)


# ==================== Device Endpoints ====================


@router.get("/devices", response_model=DeviceListResponse)
async def list_devices(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id_flexible),
):
    """
    List all WhatsApp devices for the current user.

    Supports both session-based (Bearer token) and API key authentication.
    """
    devices = await service.get_devices(db, user_id)
    return DeviceListResponse(devices=devices, total=len(devices))


@router.post("/devices", response_model=dict, status_code=201)
async def create_device(
    device_data: DeviceCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Create a new WhatsApp device and start linking process.
    Returns QR code for scanning.
    """
    # Lock before get_device_limit so concurrent first requests cannot race its
    # unique subscription insert. That helper may commit and release the lock.
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:user_id, 0))"),
        {"user_id": user_id},
    )
    device_limit = await get_device_limit(db, user_id)

    # Re-acquire after get_device_limit because creating the initial free
    # subscription commits. All creators take user -> global GOWA lock order.
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:user_id, 0))"),
        {"user_id": user_id},
    )
    result = await db.execute(
        select(func.count())
        .select_from(WhatsAppDeviceDB)
        .where(WhatsAppDeviceDB.user_id == user_id)
    )
    device_count = result.scalar_one()
    if device_count >= device_limit:
        device_label = "device" if device_limit == 1 else "devices"
        raise HTTPException(
            status_code=403,
            detail=(
                "Device limit reached for your current plan "
                f"({device_limit} {device_label}). "
                "Contact your administrator to link more devices."
            ),
        )

    device, qr = await service.create_device(db, user_id, device_data.name)
    return {"device": device.model_dump(), "qr": qr.model_dump()}


@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id_flexible),
):
    """
    Get a specific WhatsApp device.

    Supports both session-based (Bearer token) and API key authentication.
    """
    device = await service.get_device(db, device_id, user_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.delete("/devices/{device_id}", status_code=200)
async def delete_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Delete/unlink a WhatsApp device.
    """
    deleted = await service.delete_device(db, device_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"message": "Device deleted successfully"}


@router.get("/devices/{device_id}/qr", response_model=QRCodeResponse)
async def get_device_qr(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    force_refresh: bool = False,  # Optional query param to bypass cache
):
    """
    Get QR code for a device (for re-scanning if needed).
    Uses caching to prevent repeated QR generation within 10 seconds.
    Note: device_id can be the UUID from DB or the GOWA device_id.
    """
    import uuid as uuid_lib
    from datetime import timedelta

    from sqlalchemy import select

    from app.modules.whatsapp.models import WhatsAppDeviceDB
    from app.modules.whatsapp.whatsapp_client import get_gowa_client

    # Try to find device by UUID first (from DB id field)
    try:
        result = await db.execute(
            select(WhatsAppDeviceDB)
            .where(WhatsAppDeviceDB.id == uuid_lib.UUID(device_id))
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
        raise HTTPException(status_code=404, detail="Device not found")

    # Simple in-memory cache for QR codes (10 second TTL to avoid repeated requests)
    cache_key = str(db_device.device_id)

    # Check cache unless force_refresh is True
    if not force_refresh and cache_key in _qr_cache:
        cached_data, cached_at = _qr_cache[cache_key]
        if datetime.utcnow() - cached_at < timedelta(seconds=10):
            logger.debug(f"Using cached QR for device {db_device.device_id}")
            return cached_data

    # Get QR from GOWA using GOWA device_id
    try:
        gowa_client = get_gowa_client()
        qr_data = await gowa_client.login_device_qr(db_device.device_id)

        # Check if already logged in
        if qr_data.get("code") == "ALREADY_LOGGED_IN":
            response = QRCodeResponse(
                device_id=str(db_device.device_id),
                qr_code=None,
                status="connected",
                message="Device already connected",
            )
            # Cache the response
            _qr_cache[cache_key] = (response, datetime.utcnow())
            return response

        # Get QR link
        results = qr_data.get("results", {})
        qr_link = results.get("qr_link") or qr_data.get("qr_link")

        # Download and convert to base64
        qr_base64 = None
        if qr_link:
            qr_base64 = await gowa_client.download_qr_as_base64(qr_link)

        response = QRCodeResponse(
            device_id=str(db_device.device_id),
            qr_code=qr_base64,
            status="pending",
            message="Scan QR code with WhatsApp",
        )

        # Cache the response
        _qr_cache[cache_key] = (response, datetime.utcnow())

        return response

    except Exception as e:
        error_response = QRCodeResponse(
            device_id=str(db_device.device_id),
            qr_code=None,
            status="error",
            message=str(e),
        )
        # Don't cache errors
        return error_response


@router.get("/devices/{device_id}/status", response_model=dict)
async def get_device_status(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    force_refresh: bool = False,  # Optional query param to bypass cache
):
    """
    Get connection status of a device with caching to improve performance.
    Note: device_id can be the UUID from DB or the GOWA device_id.
    """
    import uuid as uuid_lib
    from datetime import timedelta

    from sqlalchemy import select

    from app.modules.whatsapp.models import WhatsAppDeviceDB
    from app.modules.whatsapp.whatsapp_client import get_gowa_client

    # Try to find device by UUID first (from DB id field)
    try:
        result = await db.execute(
            select(WhatsAppDeviceDB)
            .where(WhatsAppDeviceDB.id == uuid_lib.UUID(device_id))
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
        raise HTTPException(status_code=404, detail="Device not found")

    # Simple in-memory cache for device status (3 second TTL)
    cache_key = str(db_device.device_id)

    # Check cache unless force_refresh is True
    if not force_refresh and cache_key in _status_cache:
        cached_data, cached_at = _status_cache[cache_key]
        if datetime.utcnow() - cached_at < timedelta(seconds=3):
            logger.debug(f"Using cached status for device {db_device.device_id}")
            return cached_data

    # Sync status with GOWA before returning
    needs_db_update = False
    try:
        gowa_client = get_gowa_client()
        device_info = await gowa_client.get_device_info(str(db_device.device_id))

        gowa_status = device_info.get("state") or device_info.get("status", "unknown")
        jid = device_info.get("jid") or device_info.get("phone")

        # Only mark as connected if JID exists (QR was actually scanned)
        # GOWA v8 uses "logged_in" state when device is connected
        if gowa_status in ["connected", "authenticated", "logged_in"] and jid:
            if db_device.status != "connected":
                db_device.status = "connected"
                needs_db_update = True
            if not db_device.connected_at:
                db_device.connected_at = datetime.utcnow()
                needs_db_update = True
        elif gowa_status in ["disconnected", "logged_out"]:
            if db_device.status != "disconnected":
                db_device.status = "disconnected"
                needs_db_update = True
        elif gowa_status in ["pending", "qr_generated"] or (gowa_status == "connected" and not jid):
            # If GOWA says connected but no JID, it's actually pending (QR not scanned)
            if db_device.status != "pending":
                db_device.status = "pending"
                needs_db_update = True

        # Update phone if available
        if jid and not db_device.phone:
            db_device.phone = jid.replace("@s.whatsapp.net", "")
            needs_db_update = True

        # Only commit if something changed
        if needs_db_update:
            await db.commit()
            await db.refresh(db_device)

    except Exception as e:
        logger.warning(f"Could not sync device status from GOWA: {e}")

    # Build response
    response_data = {
        "device_id": str(db_device.device_id),
        "status": str(db_device.status),
        "phone": str(db_device.phone) if db_device.phone else None,
        "name": str(db_device.name) if db_device.name else None,
        "connected_at": db_device.connected_at.isoformat() if db_device.connected_at else None,
    }

    # Cache the response
    _status_cache[cache_key] = (response_data, datetime.utcnow())

    return response_data


@router.post("/devices/cleanup/orphaned", status_code=200)
async def cleanup_orphaned_devices(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_admin_user),
):
    """
    Clean up orphaned devices (devices that exist in GOWA but not in DB).
    This is useful for manual maintenance and troubleshooting.
    """
    from app.modules.whatsapp.service import _cleanup_orphaned_devices

    try:
        count = await _cleanup_orphaned_devices(db)
        return {"message": f"Cleaned up {count} orphaned device(s)", "count": count}
    finally:
        # Explicitly end the transaction so the global xact lock is released
        # before response serialization or dependency teardown.
        await db.rollback()


# ==================== Message Endpoints ====================


@router.post("/devices/{device_id}/send", response_model=SendMessageResponse)
async def send_message(
    device_id: str,
    message_data: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id_flexible),
):
    """
    Send a WhatsApp message using a specific device.

    Supports both session-based (Bearer token) and API key authentication.
    """
    import uuid as uuid_lib

    from sqlalchemy import select

    from app.modules.whatsapp.models import WhatsAppDeviceDB

    # Get device to retrieve phone number
    try:
        result_dev = await db.execute(
            select(WhatsAppDeviceDB)
            .where(WhatsAppDeviceDB.id == uuid_lib.UUID(device_id))
            .where(WhatsAppDeviceDB.user_id == user_id)
        )
        db_device = result_dev.scalar_one_or_none()
    except (ValueError, AttributeError):
        db_device = None

    if not db_device:
        result_dev = await db.execute(
            select(WhatsAppDeviceDB)
            .where(WhatsAppDeviceDB.device_id == device_id)
            .where(WhatsAppDeviceDB.user_id == user_id)
        )
        db_device = result_dev.scalar_one_or_none()

    result = await service.send_message(
        db, device_id, user_id, message_data.phone, message_data.message
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    # Broadcast sent message to WebSocket subscribers
    if result.success and result.message_id and db_device:
        try:
            await ws_manager.broadcast_message_event(
                str(db_device.id),
                "message_sent",
                {
                    "message_id": result.message_id,
                    "from": str(db_device.phone) if db_device.phone else "",
                    "from_phone": str(db_device.phone) if db_device.phone else "",
                    "to": message_data.phone,
                    "to_phone": message_data.phone,
                    "body": message_data.message,
                    "type": "text",
                    "is_from_me": True,
                    "status": "sent",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            logger.info(
                f"Broadcasted message_sent via WebSocket: "
                f"from={db_device.phone}, to={message_data.phone}"
            )
        except Exception as e:
            logger.error(f"Error broadcasting sent message via WebSocket: {e}")

    return result


@router.get("/devices/{device_id}/messages", response_model=MessageListResponse)
async def list_messages(
    device_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    List messages for a specific device.
    Note: device_id can be the UUID from DB or the GOWA device_id.
    """
    import uuid as uuid_lib

    from sqlalchemy import select

    from app.modules.whatsapp.models import WhatsAppDeviceDB, WhatsAppMessageDB

    # Try to find device by UUID first (from DB id field)
    try:
        result = await db.execute(
            select(WhatsAppDeviceDB)
            .where(WhatsAppDeviceDB.id == uuid_lib.UUID(device_id))
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
        raise HTTPException(status_code=404, detail="Device not found")

    # Get messages for this device
    result = await db.execute(
        select(WhatsAppMessageDB)
        .where(WhatsAppMessageDB.device_id == db_device.id)
        .order_by(WhatsAppMessageDB.timestamp.desc())
        .limit(limit)
        .offset(offset)
    )
    messages = result.scalars().all()

    # Get total count
    from sqlalchemy import func

    count_result = await db.execute(
        select(func.count())
        .select_from(WhatsAppMessageDB)
        .where(WhatsAppMessageDB.device_id == db_device.id)
    )
    total = count_result.scalar() or 0

    from app.modules.whatsapp.models import MessageResponse

    message_responses = [MessageResponse.model_validate(m) for m in messages]

    return MessageListResponse(messages=message_responses, total=total, limit=limit, offset=offset)


# ==================== Chat Endpoints ====================


@router.get("/chats")
async def list_chats(
    device_id: str = Query(None, description="Optional device ID to filter chats"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Get all chats (conversations) for the user.
    Groups messages by phone number and returns summary for each conversation.
    """
    chats = await service.get_chats(db, user_id, device_id)

    return {
        "chats": chats,
        "total": len(chats),
    }


@router.get("/chats/{phone}/messages", response_model=MessageListResponse)
async def get_chat_messages(
    phone: str,
    device_id: str = Query(..., description="Device ID to get messages from"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Get all messages for a specific chat (conversation with a phone number).
    """
    import uuid as uuid_lib

    from sqlalchemy import or_, select

    from app.modules.whatsapp.models import WhatsAppDeviceDB, WhatsAppMessageDB

    # Find device
    try:
        result = await db.execute(
            select(WhatsAppDeviceDB)
            .where(WhatsAppDeviceDB.id == uuid_lib.UUID(device_id))
            .where(WhatsAppDeviceDB.user_id == user_id)
        )
        db_device = result.scalar_one_or_none()
    except (ValueError, AttributeError):
        db_device = None

    if not db_device:
        result = await db.execute(
            select(WhatsAppDeviceDB)
            .where(WhatsAppDeviceDB.device_id == device_id)
            .where(WhatsAppDeviceDB.user_id == user_id)
        )
        db_device = result.scalar_one_or_none()

    if not db_device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Get messages for this chat (both sent and received)
    result = await db.execute(
        select(WhatsAppMessageDB)
        .where(WhatsAppMessageDB.device_id == db_device.id)
        .where(
            or_(
                WhatsAppMessageDB.from_phone == phone,
                WhatsAppMessageDB.to_phone == phone,
            )
        )
        .order_by(WhatsAppMessageDB.timestamp.desc())
        .limit(limit)
        .offset(offset)
    )
    messages = result.scalars().all()

    # Get total count
    from sqlalchemy import func

    count_result = await db.execute(
        select(func.count())
        .select_from(WhatsAppMessageDB)
        .where(WhatsAppMessageDB.device_id == db_device.id)
        .where(
            or_(
                WhatsAppMessageDB.from_phone == phone,
                WhatsAppMessageDB.to_phone == phone,
            )
        )
    )
    total = count_result.scalar() or 0

    from app.modules.whatsapp.models import MessageResponse

    message_responses = [MessageResponse.model_validate(m) for m in messages]

    return MessageListResponse(messages=message_responses, total=total, limit=limit, offset=offset)


# ==================== Webhook Endpoints ====================


async def _process_webhook_request(
    request: Request,
    db: AsyncSession,
    instance_port: int = None,
    x_webhook_secret: str = None,
    x_hub_signature_256: str = None,
):
    """
    Common webhook processing logic.

    Args:
        request: FastAPI request
        db: Database session
        instance_port: GOWA instance port that sent the webhook
        x_webhook_secret: Webhook secret header (GOWA <= v8, plaintext secret)
        x_hub_signature_256: HMAC-SHA256 signature header (GOWA >= v9, "sha256=<hex>")
    """
    # Get all headers (never log them: they carry the webhook secret)
    headers = dict(request.headers)
    logger.info(f"Webhook received, instance_port: {instance_port}")

    # Validate webhook secret - check multiple possible headers
    expected_secret = settings.WHATSAPP_WEBHOOK_SECRET
    received_secret = (
        x_webhook_secret
        or x_hub_signature_256
        or headers.get("x-webhook-secret")
        or headers.get("webhook-secret")
        or headers.get("x-hub-signature-256")
    )

    if expected_secret:
        # A secret is configured: every request must carry a valid one.
        # Missing header is rejected too, otherwise an attacker can bypass
        # validation simply by omitting it.
        if not received_secret:
            logger.warning("Webhook rejected: no secret provided")
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

        if not hmac.compare_digest(received_secret, expected_secret):
            # Try HMAC validation as fallback
            body = await request.body()
            expected_signature = hmac.new(
                expected_secret.encode(), body, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(
                received_secret, expected_signature
            ) and not hmac.compare_digest(received_secret, f"sha256={expected_signature}"):
                logger.warning("Webhook rejected: invalid secret")
                raise HTTPException(status_code=401, detail="Invalid webhook secret")

    # Parse body
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Error parsing webhook body: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Extract webhook data
    # GOWA v8 sends: {"event": "message", "device_id": "phone@s.whatsapp.net", "payload": {...}}
    webhook_type = payload.get("event") or payload.get("type", "message")
    device_id = payload.get("device_id") or payload.get("deviceId")

    # If no device_id, try to extract phone from "from" field in payload
    if not device_id:
        inner_payload = payload.get("payload", {})
        from_field = inner_payload.get("from", "") or payload.get("from", "")
        if from_field:
            # Extract phone number from "15551234567@s.whatsapp.net"
            device_id = from_field.split("@")[0] if "@" in from_field else from_field

    # GOWA v8 uses "payload" key, older versions use "data"
    data = payload.get("payload") or payload.get("data", payload)

    logger.info(
        f"Webhook received - type: {webhook_type}, device_id: {device_id}, port: {instance_port}"
    )

    # Process webhook with instance_port for accurate device lookup
    try:
        await service.process_webhook(db, webhook_type, device_id, data, instance_port, ws_manager)
        return {"status": "processed"}
    except Exception:
        logger.exception("Error processing webhook")
        return {"status": "error"}


@router.post("/webhook/{instance_port}", status_code=200)
@limiter.limit(RateLimits.WEBHOOK)
async def receive_webhook_with_port(
    instance_port: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_webhook_secret: str = Header(None, alias="X-Webhook-Secret"),
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
):
    """
    Receive webhooks from a specific GOWA instance.
    The port in the URL identifies which GOWA instance sent the webhook.
    """
    return await _process_webhook_request(
        request, db, instance_port, x_webhook_secret, x_hub_signature_256
    )


@router.post("/webhook", status_code=200)
@limiter.limit(RateLimits.WEBHOOK)
async def receive_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_webhook_secret: str = Header(None, alias="X-Webhook-Secret"),
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
):
    """
    Receive webhooks from GOWA (backwards compatible endpoint without port).
    This endpoint does not require JWT authentication but validates webhook secret.
    """
    return await _process_webhook_request(
        request, db, None, x_webhook_secret, x_hub_signature_256
    )
