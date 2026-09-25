import logging
import os

import firebase_admin
from firebase_admin import credentials

logger = logging.getLogger(__name__)

_firebase_app = None


def initialize_firebase() -> firebase_admin.App:
    """
    Initialize Firebase Admin SDK.
    Uses service account credentials from path defined in settings.
    """
    global _firebase_app

    if _firebase_app is not None:
        return _firebase_app

    if firebase_admin._apps:
        _firebase_app = firebase_admin.get_app()
        return _firebase_app

    from app.config.settings import settings

    service_account_path = settings.FIREBASE_SERVICE_ACCOUNT_PATH

    if not os.path.exists(service_account_path):
        raise FileNotFoundError(
            f"Firebase service account file not found at: {service_account_path}"
        )

    cred = credentials.Certificate(service_account_path)
    _firebase_app = firebase_admin.initialize_app(cred)
    logger.info(
        f"Firebase Admin SDK initialized for project: {settings.FIREBASE_PROJECT_ID}"
    )

    return _firebase_app


def get_firebase_app() -> firebase_admin.App:
    """Get the initialized Firebase app instance."""
    if _firebase_app is None:
        return initialize_firebase()
    return _firebase_app
