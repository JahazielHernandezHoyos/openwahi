"""Client for communicating with GOWA (go-whatsapp-web-multidevice) v8 API."""

import logging
import os
from typing import Dict, List, Optional

import httpx

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Detect if running in Docker (check for Docker network or env var)
IS_DOCKER = os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER", False)


class GOWAClient:
    """
    Client for GOWA (go-whatsapp-web-multidevice) v8 API.

    v8 supports multiple devices in a single server instance.
    """

    def __init__(self, host: str = "localhost", port: int = 3000):
        """
        Initialize GOWA client.

        Args:
            host: GOWA server host (use 'whatsapp' for Docker, 'localhost' otherwise)
            port: GOWA server port (default: 3000)
        """
        self.host = host
        self.port = port

        # Use Docker hostname if running in Docker
        if IS_DOCKER and host == "localhost":
            self.host = "whatsapp"

        self.base_url = f"http://{self.host}:{port}"
        logger.info(f"GOWA client initialized, base_url: {self.base_url}")

        self.auth = (settings.WHATSAPP_USER, settings.WHATSAPP_PASSWORD)
        self.timeout = 30.0

    # ==================== Device Management API ====================

    async def list_devices(self) -> List[Dict]:
        """
        List all registered devices.

        Endpoint: GET /devices

        Returns:
            List of devices with their status
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/devices", auth=self.auth)
                response.raise_for_status()
                data = response.json()

                # v8 returns: {"code": "SUCCESS", "results": {"devices": [...]}}
                if isinstance(data, dict):
                    results = data.get("results", {})
                    if isinstance(results, dict):
                        return results.get("devices", [])
                    return results or []
                return data
        except httpx.HTTPError as e:
            logger.error(f"Error listing devices: {e}")
            raise

    async def add_device(self, name: Optional[str] = None) -> Dict:
        """
        Add a new device (creates session, returns device_id).

        Endpoint: POST /devices

        Args:
            name: Optional device name

        Returns:
            dict with device_id and status
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {}
                if name:
                    payload["name"] = name

                response = await client.post(
                    f"{self.base_url}/devices", auth=self.auth, json=payload
                )
                response.raise_for_status()
                data = response.json()

                # v8 returns: {"code": "SUCCESS", "results": {"device_id": "..."}}
                results = data.get("results", {})
                return results
        except httpx.HTTPError as e:
            logger.error(f"Error adding device: {e}")
            raise

    async def get_device_info(self, device_id: str) -> Dict:
        """
        Get information about a specific device.

        Endpoint: GET /devices/:device_id

        Args:
            device_id: Device ID

        Returns:
            dict with device info
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/devices/{device_id}", auth=self.auth)
                response.raise_for_status()
                data = response.json()

                # v8 returns: {"code": "SUCCESS", "results": {...}}
                return data.get("results", {})
        except httpx.HTTPError as e:
            logger.error(f"Error getting device info for {device_id}: {e}")
            raise

    async def remove_device(self, device_id: str) -> Dict:
        """
        Remove/unlink a device.

        Endpoint: DELETE /devices/:device_id

        Args:
            device_id: Device to remove

        Returns:
            dict with removal status
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    f"{self.base_url}/devices/{device_id}", auth=self.auth
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error removing device {device_id}: {e}")
            raise

    async def login_device_qr(self, device_id: str) -> Dict:
        """
        Get QR code for device login.

        Endpoint: GET /app/login (with X-Device-Id header)
        Note: GOWA v8 uses /app/login with device ID in header, not /devices/:id/login

        Args:
            device_id: Device to login

        Returns:
            dict with QR code data
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/app/login",
                    auth=self.auth,
                    headers={"X-Device-Id": device_id},
                )

                # Parse response
                try:
                    data = response.json()
                except Exception:
                    data = {"message": response.text}

                # Check for "already logged in" indicators
                message = str(data.get("message", "")).lower()
                if (
                    response.status_code == 400
                    or "already logged in" in message
                    or "already connected" in message
                ):
                    return {
                        "code": "ALREADY_LOGGED_IN",
                        "message": "Device already connected",
                        "results": {},
                    }

                response.raise_for_status()
                return data
        except httpx.HTTPError as e:
            error_msg = str(e).lower()
            if "already logged in" in error_msg or "400" in error_msg:
                return {
                    "code": "ALREADY_LOGGED_IN",
                    "message": "Device already connected",
                    "results": {},
                }
            logger.error(f"Error getting QR for device {device_id}: {e}")
            raise

    async def login_device_code(self, device_id: str, phone: str) -> Dict:
        """
        Generate pairing code for device login.

        Endpoint: POST /devices/:device_id/login/code

        Args:
            device_id: Device to login
            phone: Phone number (with country code)

        Returns:
            dict with pairing code
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/devices/{device_id}/login/code",
                    auth=self.auth,
                    json={"phone": phone},
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error getting pairing code for device {device_id}: {e}")
            raise

    async def logout_device(self, device_id: str) -> Dict:
        """
        Logout/disconnect a device.

        Endpoint: POST /devices/:device_id/logout

        Args:
            device_id: Device to logout

        Returns:
            dict with logout status
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/devices/{device_id}/logout", auth=self.auth
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error logging out device {device_id}: {e}")
            raise

    async def reconnect_device(self, device_id: str) -> Dict:
        """
        Reconnect a disconnected device.

        Endpoint: POST /devices/:device_id/reconnect

        Args:
            device_id: Device to reconnect

        Returns:
            dict with reconnect status
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/devices/{device_id}/reconnect", auth=self.auth
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error reconnecting device {device_id}: {e}")
            raise

    async def get_device_status(self, device_id: str) -> Dict:
        """
        Get connection status of a device.

        Endpoint: GET /devices/:device_id/status

        Args:
            device_id: Device to check

        Returns:
            dict with device status (connected, disconnected, pending, etc.)
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/devices/{device_id}/status", auth=self.auth
                )
                response.raise_for_status()
                data = response.json()

                # v8 returns: {"code": "SUCCESS", "results": {"status": "connected", ...}}
                return data.get("results", {})
        except httpx.HTTPError as e:
            logger.error(f"Error getting device status for {device_id}: {e}")
            raise

    # ==================== Presence/Typing API ====================

    async def send_typing_indicator(self, device_id: str, phone: str, start: bool = True) -> Dict:
        """
        Send typing indicator (composing/paused state).

        Endpoint: POST /send/chat-presence
        Header: X-Device-Id (required)

        Args:
            device_id: Device to send from
            phone: Recipient phone number (will be formatted to WhatsApp format)
            start: True to start typing indicator, False to stop

        Returns:
            dict with status
        """
        # Format phone number for WhatsApp (add @s.whatsapp.net if not present)
        formatted_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
        if not formatted_phone.endswith("@s.whatsapp.net"):
            formatted_phone = f"{formatted_phone}@s.whatsapp.net"

        action = "start" if start else "stop"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/send/chat-presence",
                    auth=self.auth,
                    headers={"X-Device-Id": device_id},
                    json={"phone": formatted_phone, "action": action},
                )

                logger.debug(f"Typing indicator {action} sent to {phone} from device {device_id}")

                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error sending typing indicator to {phone} from device {device_id}: {e}")
            return {"success": False, "error": str(e)}

    # ==================== Message Sending API ====================

    async def send_message(self, device_id: str, phone: str, message: str) -> Dict:
        """
        Send a text message using a specific device.

        Endpoint: POST /send/message
        Header: X-Device-Id (required)

        Args:
            device_id: Device to send from
            phone: Recipient phone number (will be formatted to WhatsApp format)
            message: Text message to send

        Returns:
            dict with send status and message ID
            Format: {"success": true/false, "message_id": "...", "error": "..."}
        """
        # Format phone number for WhatsApp (add @s.whatsapp.net if not present)
        formatted_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
        if not formatted_phone.endswith("@s.whatsapp.net"):
            formatted_phone = f"{formatted_phone}@s.whatsapp.net"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/send/message",
                    auth=self.auth,
                    headers={"X-Device-Id": device_id},
                    json={"phone": formatted_phone, "message": message},
                )

                logger.info(f"GOWA send_message response status: {response.status_code}")
                logger.info(f"GOWA send_message response body: {response.text[:500]}")

                response.raise_for_status()
                result = response.json()

                # Normalize response format
                # GOWA v8 may return different formats
                if "status" in result:
                    # Format: {"status": "success", "data": {...}}
                    return {
                        "success": result.get("status") == "success",
                        "message_id": result.get("data", {}).get("message_id"),
                        "data": result.get("data"),
                    }
                else:
                    # Return as-is and hope it has needed fields
                    return result

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error sending message from device {device_id} to {phone}: "
                f"Status {e.response.status_code}, Response: {e.response.text[:500]}"
            )
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            }
        except httpx.HTTPError as e:
            logger.error(f"Error sending message from device {device_id} to {phone}: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(
                f"Unexpected error sending message from device {device_id} to {phone}: {e}"
            )
            return {"success": False, "error": str(e)}

    async def download_media(self, media_url: str) -> bytes:
        """
        Download media file (audio, image, document) from GOWA.

        Args:
            media_url: URL of the media as provided by GOWA in the webhook payload

        Returns:
            Raw bytes of the media file

        Raises:
            httpx.HTTPError: If the download fails
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(media_url, auth=self.auth)
                response.raise_for_status()
                return response.content
        except httpx.HTTPError as e:
            logger.error(f"Error downloading media from {media_url}: {e}")
            raise

    async def send_image(
        self, device_id: str, phone: str, image_url: str, caption: Optional[str] = None
    ) -> Dict:
        """
        Send an image message.

        Args:
            device_id: Device to send from
            phone: Recipient phone number
            image_url: URL or base64 of image
            caption: Optional caption

        Returns:
            dict with send status
        """
        formatted_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
        if not formatted_phone.endswith("@s.whatsapp.net"):
            formatted_phone = f"{formatted_phone}@s.whatsapp.net"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {"phone": formatted_phone, "image": image_url}
                if caption:
                    payload["caption"] = caption

                response = await client.post(
                    f"{self.base_url}/send/image",
                    auth=self.auth,
                    headers={"X-Device-Id": device_id},
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error sending image from device {device_id}: {e}")
            raise

    # ==================== User/Device Info API ====================

    async def get_user_info(self, device_id: str) -> Dict:
        """
        Get user info for a device.

        Args:
            device_id: Device ID

        Returns:
            dict with user info (phone, name, etc.)
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/user/info",
                    auth=self.auth,
                    headers={"X-Device-Id": device_id},
                )
                response.raise_for_status()
                data = response.json()
                return data.get("results", {})
        except httpx.HTTPError as e:
            logger.error(f"Error getting user info for device {device_id}: {e}")
            raise

    async def get_user_contacts(self, device_id: str) -> List[Dict]:
        """
        Get contacts for a device.

        Args:
            device_id: Device ID

        Returns:
            List of contacts
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/user/my/contacts",
                    auth=self.auth,
                    headers={"X-Device-Id": device_id},
                )
                response.raise_for_status()
                data = response.json()
                results = data.get("results", {})
                return results.get("contacts", [])
        except httpx.HTTPError as e:
            logger.error(f"Error getting contacts for device {device_id}: {e}")
            raise

    async def get_chats(self, device_id: str, limit: int = 50, offset: int = 0) -> Dict:
        """
        Get chat list for a device.

        Args:
            device_id: Device ID
            limit: Number of chats to return
            offset: Pagination offset

        Returns:
            dict with chats and pagination info
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/chats",
                    auth=self.auth,
                    headers={"X-Device-Id": device_id},
                    params={"limit": limit, "offset": offset},
                )
                response.raise_for_status()
                data = response.json()
                return data.get("results", {})
        except httpx.HTTPError as e:
            logger.error(f"Error getting chats for device {device_id}: {e}")
            raise

    # ==================== Utility Methods ====================

    async def download_qr_as_base64(self, qr_url: str) -> Optional[str]:
        """
        Download QR image and convert to base64.

        Args:
            qr_url: URL of the QR image

        Returns:
            Base64 encoded image string or None
        """
        import base64

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(qr_url, auth=self.auth)
                response.raise_for_status()
                image_data = base64.b64encode(response.content).decode("utf-8")
                return f"data:image/png;base64,{image_data}"
        except httpx.HTTPError as e:
            logger.error(f"Error downloading QR image: {e}")
            return None

    async def health_check(self) -> bool:
        """
        Check if GOWA server is reachable.

        Returns:
            True if server is reachable, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Use /devices endpoint for v8 instead of /app/status
                response = await client.get(f"{self.base_url}/devices", auth=self.auth)
                return response.status_code == 200
        except Exception:
            return False


# Singleton instance
_gowa_client: Optional[GOWAClient] = None


def get_gowa_client() -> GOWAClient:
    """
    Get the singleton GOWA client instance.

    Returns:
        GOWAClient instance
    """
    global _gowa_client
    if _gowa_client is None:
        host = "localhost"
        port = 3000

        # Override from environment if available
        if os.environ.get("GOWA_HOST"):
            host = os.environ.get("GOWA_HOST")
        if os.environ.get("GOWA_PORT"):
            port = int(os.environ.get("GOWA_PORT"))

        _gowa_client = GOWAClient(host=host, port=port)
    return _gowa_client


# Convenience alias
gowa_client = get_gowa_client()
