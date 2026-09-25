"""
WebSocket manager for real-time WhatsApp message notifications.

This module extends the generic WebSocket manager with WhatsApp-specific
functionality for device connections and message broadcasting.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import WebSocket

from app.core.websocket import WebSocketManager

logger = logging.getLogger(__name__)


class WhatsAppWebSocketManager(WebSocketManager):
    """
    WebSocket manager specialized for WhatsApp device connections.

    Extends the generic WebSocketManager with WhatsApp-specific methods
    for device status updates and message event broadcasting.

    In this context:
    - room_id = device_id (each device is a "room")
    - user_id = user who owns the device
    """

    def __init__(self):
        super().__init__(name="whatsapp")

    async def connect(
        self,
        websocket: WebSocket,
        device_id: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Accept a new WebSocket connection for a WhatsApp device.

        Args:
            websocket: The WebSocket connection
            device_id: Device UUID to subscribe to
            user_id: User ID for authorization tracking
            metadata: Optional additional metadata

        Returns:
            True if connection was successful, False otherwise
        """
        # Use device_id as room_id
        return await super().connect(
            websocket=websocket,
            room_id=device_id,
            user_id=user_id,
            metadata={"device_id": device_id, **(metadata or {})},
        )

    def disconnect(
        self,
        websocket: WebSocket,
        device_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """
        Remove a WebSocket connection.

        Args:
            websocket: The WebSocket connection to remove
            device_id: Device UUID
            user_id: Optional user ID for cleanup
        """
        super().disconnect(websocket, room_id=device_id, user_id=user_id)

    async def send_personal_message(
        self,
        message: Dict[str, Any],
        websocket: WebSocket,
    ) -> bool:
        """
        Send a message to a specific WebSocket connection.

        Args:
            message: Dictionary to send as JSON
            websocket: Target WebSocket connection

        Returns:
            True if successful
        """
        return await self.send_to_connection(websocket, message)

    async def broadcast_to_device(
        self,
        device_id: str,
        message: Dict[str, Any],
    ) -> int:
        """
        Broadcast a message to all connections subscribed to a device.

        Args:
            device_id: Device UUID to broadcast to
            message: Dictionary to send as JSON

        Returns:
            Number of connections that received the message
        """
        return await self.broadcast_to_room(device_id, message)

    async def broadcast_message_event(
        self,
        device_id: str,
        event_type: str,
        message_data: Dict[str, Any],
    ) -> int:
        """
        Broadcast a message-related event to all subscribers of a device.

        Args:
            device_id: Device UUID
            event_type: Type of event (e.g., 'new_message', 'message_ack', 'message_read')
            message_data: Message data to broadcast

        Returns:
            Number of connections that received the message
        """
        payload = {
            "type": event_type,
            "device_id": device_id,
            "data": message_data,
            "timestamp": message_data.get("timestamp"),
        }

        count = await self.broadcast_to_device(device_id, payload)

        logger.info(
            f"Broadcasted {event_type} event to device {device_id}: "
            f"message_id={message_data.get('message_id', 'N/A')}, recipients={count}"
        )

        return count

    async def broadcast_device_status(
        self,
        device_id: str,
        status: str,
        phone: Optional[str] = None,
        message: Optional[str] = None,
    ) -> int:
        """
        Broadcast device connection status change.

        Args:
            device_id: Device UUID
            status: New status (e.g., 'connected', 'disconnected', 'pending')
            phone: Optional phone number
            message: Optional status message

        Returns:
            Number of connections that received the message
        """
        payload = {
            "type": "device_status",
            "device_id": device_id,
            "status": status,
            "phone": phone,
            "message": message,
        }

        count = await self.broadcast_to_device(device_id, payload)

        logger.info(f"Broadcasted device status to {device_id}: status={status}, recipients={count}")

        return count

    async def broadcast_devices_update(
        self,
        user_id: str,
        devices: list,
        event: str = "devices_updated",
    ) -> int:
        """
        Broadcast devices list update to all connections of a user.

        Args:
            user_id: User ID to broadcast to
            devices: List of device data
            event: Event type (devices_updated, device_created, device_deleted)

        Returns:
            Number of connections that received the message
        """
        payload = {
            "type": event,
            "devices": devices,
        }

        # Broadcast to all devices the user is subscribed to
        total_sent = 0
        for device_id in self.get_user_rooms(user_id):
            count = await self.broadcast_to_device(device_id, payload)
            total_sent += count

        if total_sent > 0:
            logger.info(f"Broadcasted {event} to user {user_id}: {len(devices)} devices, {total_sent} recipients")

        return total_sent

    def get_active_connections_count(self, device_id: Optional[str] = None) -> int:
        """
        Get count of active WebSocket connections.

        Args:
            device_id: Optional device ID to count connections for

        Returns:
            Number of active connections
        """
        return self.get_connection_count(room_id=device_id)

    def get_subscribed_devices(self, user_id: str) -> set:
        """
        Get list of device IDs a user is subscribed to.

        Args:
            user_id: User ID

        Returns:
            Set of device IDs
        """
        return self.get_user_rooms(user_id)


# Global WebSocket manager instance for WhatsApp
ws_manager = WhatsAppWebSocketManager()
