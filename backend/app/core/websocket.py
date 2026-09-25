"""
Generic WebSocket manager for real-time notifications.

This module provides a reusable WebSocket manager that can be used by any
feature module (WhatsApp, notifications, chat, etc.) for real-time updates.

Usage:
    from app.core.websocket import WebSocketManager

    # Create a manager for your feature
    ws_manager = WebSocketManager("my_feature")

    # In your WebSocket endpoint
    await ws_manager.connect(websocket, room_id="room123", user_id="user456")

    # Broadcast to a room
    await ws_manager.broadcast_to_room("room123", {"type": "update", "data": {...}})
"""

import json
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any, Dict, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Generic WebSocket connection manager.

    Manages WebSocket connections organized by "rooms" (channels/topics).
    Clients connect to specific rooms and receive broadcasts for that room.

    Attributes:
        name: Identifier for this manager (used in logging)
        active_connections: Map of room_id -> set of WebSocket connections
        user_subscriptions: Map of user_id -> set of room_ids
        connection_metadata: Map of websocket -> metadata dict
    """

    def __init__(self, name: str = "default"):
        """
        Initialize WebSocket manager.

        Args:
            name: Identifier for this manager (e.g., "whatsapp", "notifications")
        """
        self.name = name
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_subscriptions: Dict[str, Set[str]] = {}
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        room_id: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        accept: bool = True,
    ) -> bool:
        """
        Accept a new WebSocket connection and subscribe to a room.

        Args:
            websocket: The WebSocket connection
            room_id: Room/channel/topic to subscribe to
            user_id: User ID for authorization tracking
            metadata: Optional metadata to store with connection
            accept: Whether to accept the connection (set False if already accepted)

        Returns:
            True if connection was successful, False otherwise
        """
        try:
            if accept:
                await websocket.accept()

            # Add connection to room's connection set
            if room_id not in self.active_connections:
                self.active_connections[room_id] = set()
            self.active_connections[room_id].add(websocket)

            # Track user subscription
            if user_id not in self.user_subscriptions:
                self.user_subscriptions[user_id] = set()
            self.user_subscriptions[user_id].add(room_id)

            # Store metadata
            self.connection_metadata[websocket] = {
                "room_id": room_id,
                "user_id": user_id,
                "connected_at": datetime.utcnow().isoformat(),
                **(metadata or {}),
            }

            logger.info(
                f"[{self.name}] WebSocket connected: user={user_id}, room={room_id}, "
                f"total_connections={len(self.active_connections.get(room_id, set()))}"
            )

            # Send connection confirmation (don't fail if this doesn't work)
            await self.send_to_connection(
                websocket,
                {
                    "type": "connection",
                    "status": "connected",
                    "room_id": room_id,
                    "message": "WebSocket connected successfully",
                },
            )

            return True

        except Exception as e:
            logger.error(f"[{self.name}] Error during WebSocket connect: {e}")
            # Clean up if we added the connection before failing
            self.disconnect(websocket, room_id, user_id)
            return False

    def disconnect(
        self,
        websocket: WebSocket,
        room_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """
        Remove a WebSocket connection.

        Args:
            websocket: The WebSocket connection to remove
            room_id: Room ID (optional, will be retrieved from metadata if not provided)
            user_id: User ID (optional, will be retrieved from metadata if not provided)
        """
        # Get room_id and user_id from metadata if not provided
        metadata = self.connection_metadata.get(websocket, {})
        room_id = room_id or metadata.get("room_id")
        user_id = user_id or metadata.get("user_id")

        if room_id and room_id in self.active_connections:
            self.active_connections[room_id].discard(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

        if user_id and user_id in self.user_subscriptions:
            self.user_subscriptions[user_id].discard(room_id)
            if not self.user_subscriptions[user_id]:
                del self.user_subscriptions[user_id]

        # Clean up metadata
        self.connection_metadata.pop(websocket, None)

        logger.info(
            f"[{self.name}] WebSocket disconnected: user={user_id}, room={room_id}, "
            f"remaining_connections={len(self.active_connections.get(room_id, set()) if room_id else [])}"
        )

    async def send_to_connection(
        self,
        websocket: WebSocket,
        message: Dict[str, Any],
    ) -> bool:
        """
        Send a message to a specific WebSocket connection.

        Args:
            websocket: Target WebSocket connection
            message: Dictionary to send as JSON

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if WebSocket is in a valid state
            if websocket.client_state.name != "CONNECTED":
                logger.warning(
                    f"[{self.name}] Cannot send: WebSocket state is {websocket.client_state.name}"
                )
                return False

            await websocket.send_json(message)
            return True
        except Exception as e:
            error_msg = str(e) if str(e) else type(e).__name__
            logger.error(f"[{self.name}] Error sending WebSocket message: {error_msg}")
            return False

    async def broadcast_to_room(
        self,
        room_id: str,
        message: Dict[str, Any],
        exclude: Optional[Set[WebSocket]] = None,
    ) -> int:
        """
        Broadcast a message to all connections in a room.

        Args:
            room_id: Room to broadcast to
            message: Dictionary to send as JSON
            exclude: Optional set of connections to exclude

        Returns:
            Number of connections that received the message
        """
        if room_id not in self.active_connections:
            logger.debug(f"[{self.name}] No active connections for room {room_id}")
            return 0

        connections = self.active_connections[room_id].copy()
        exclude = exclude or set()

        sent_count = 0
        disconnected = []

        for connection in connections:
            if connection in exclude:
                continue

            try:
                await connection.send_json(message)
                sent_count += 1
            except WebSocketDisconnect:
                logger.warning(f"[{self.name}] Connection closed during broadcast for room {room_id}")
                disconnected.append(connection)
            except Exception as e:
                logger.error(f"[{self.name}] Error broadcasting to room {room_id}: {e}")
                disconnected.append(connection)

        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

        if disconnected:
            logger.info(
                f"[{self.name}] Cleaned up {len(disconnected)} disconnected WebSocket(s) for room {room_id}"
            )

        return sent_count

    async def broadcast_to_user(
        self,
        user_id: str,
        message: Dict[str, Any],
    ) -> int:
        """
        Broadcast a message to all rooms a user is subscribed to.

        Args:
            user_id: User ID
            message: Dictionary to send as JSON

        Returns:
            Number of rooms that received the message
        """
        rooms = self.user_subscriptions.get(user_id, set()).copy()
        sent_count = 0

        for room_id in rooms:
            count = await self.broadcast_to_room(room_id, message)
            if count > 0:
                sent_count += 1

        return sent_count

    async def broadcast_event(
        self,
        room_id: str,
        event_type: str,
        data: Dict[str, Any],
        timestamp: Optional[str] = None,
    ) -> int:
        """
        Broadcast a typed event to a room.

        Args:
            room_id: Room to broadcast to
            event_type: Type of event (e.g., 'new_message', 'status_update')
            data: Event data
            timestamp: Optional timestamp (defaults to current time)

        Returns:
            Number of connections that received the message
        """
        payload = {
            "type": event_type,
            "room_id": room_id,
            "data": data,
            "timestamp": timestamp or datetime.utcnow().isoformat(),
        }

        count = await self.broadcast_to_room(room_id, payload)

        logger.info(
            f"[{self.name}] Broadcasted {event_type} event to room {room_id}: "
            f"{count} recipient(s)"
        )

        return count

    def get_connection_count(self, room_id: Optional[str] = None) -> int:
        """
        Get count of active WebSocket connections.

        Args:
            room_id: Optional room ID to count connections for

        Returns:
            Number of active connections (for specific room or total)
        """
        if room_id:
            return len(self.active_connections.get(room_id, set()))
        return sum(len(conns) for conns in self.active_connections.values())

    def get_user_rooms(self, user_id: str) -> Set[str]:
        """
        Get list of room IDs a user is subscribed to.

        Args:
            user_id: User ID

        Returns:
            Set of room IDs
        """
        return self.user_subscriptions.get(user_id, set()).copy()

    def get_room_users(self, room_id: str) -> Set[str]:
        """
        Get list of user IDs connected to a room.

        Args:
            room_id: Room ID

        Returns:
            Set of user IDs
        """
        users = set()
        for ws in self.active_connections.get(room_id, set()):
            metadata = self.connection_metadata.get(ws, {})
            if "user_id" in metadata:
                users.add(metadata["user_id"])
        return users

    def get_connection_metadata(self, websocket: WebSocket) -> Dict[str, Any]:
        """
        Get metadata for a specific connection.

        Args:
            websocket: WebSocket connection

        Returns:
            Metadata dictionary
        """
        return self.connection_metadata.get(websocket, {}).copy()

    def is_connected(self, room_id: str, user_id: Optional[str] = None) -> bool:
        """
        Check if there are active connections for a room/user.

        Args:
            room_id: Room ID to check
            user_id: Optional user ID to check

        Returns:
            True if there are active connections
        """
        if room_id not in self.active_connections:
            return False

        if user_id is None:
            return len(self.active_connections[room_id]) > 0

        for ws in self.active_connections[room_id]:
            metadata = self.connection_metadata.get(ws, {})
            if metadata.get("user_id") == user_id:
                return True
        return False
