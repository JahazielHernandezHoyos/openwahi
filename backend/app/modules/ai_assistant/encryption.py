"""
Encryption utilities for securely storing API keys.
Uses Fernet (symmetric encryption) from cryptography library.
"""

import logging
import os
from typing import Optional

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    _cipher: Optional[Fernet] = None

    @classmethod
    def _get_cipher(cls) -> Fernet:
        """Get or create cipher instance."""
        if cls._cipher is None:
            # Get encryption key from environment
            encryption_key = os.getenv("AI_ENCRYPTION_KEY")

            if not encryption_key:
                # Generate a new key if not set (for development only).
                # Never log the generated key: it decrypts every stored secret.
                logger.warning(
                    "AI_ENCRYPTION_KEY not set in environment. "
                    "Generating a temporary key; data encrypted with it is lost "
                    "on restart. Set AI_ENCRYPTION_KEY in your .env file. "
                    "THIS IS NOT SECURE FOR PRODUCTION!"
                )
                encryption_key = Fernet.generate_key().decode()

            # Ensure key is bytes
            if isinstance(encryption_key, str):
                encryption_key = encryption_key.encode()

            cls._cipher = Fernet(encryption_key)

        return cls._cipher

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: The string to encrypt

        Returns:
            Base64 encoded encrypted string
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty string")

        cipher = cls._get_cipher()
        encrypted_bytes = cipher.encrypt(plaintext.encode())
        return encrypted_bytes.decode()

    @classmethod
    def decrypt(cls, encrypted_text: str) -> str:
        """
        Decrypt an encrypted string.

        Args:
            encrypted_text: The base64 encoded encrypted string

        Returns:
            Decrypted plaintext string
        """
        if not encrypted_text:
            raise ValueError("Cannot decrypt empty string")

        try:
            cipher = cls._get_cipher()
            decrypted_bytes = cipher.decrypt(encrypted_text.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt text: {e}")
            raise ValueError("Failed to decrypt data. Key might be invalid.")


# Convenience functions
def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key."""
    return EncryptionService.encrypt(api_key)


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key."""
    return EncryptionService.decrypt(encrypted_key)
