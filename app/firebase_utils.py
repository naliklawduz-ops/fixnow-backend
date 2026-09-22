import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, messaging


def _init_firebase():
    """Initialize Firebase Admin SDK from base64-encoded env variable."""
    if firebase_admin._apps:
        return  # Already initialized

    b64_creds = os.getenv("FIREBASE_CREDENTIALS_B64")
    if not b64_creds:
        raise RuntimeError("FIREBASE_CREDENTIALS_B64 environment variable is not set")

    try:
        decoded = base64.b64decode(b64_creds).decode("utf-8")
        creds_dict = json.loads(decoded)
    except Exception as e:
        raise RuntimeError(f"Failed to decode FIREBASE_CREDENTIALS_B64: {e}")

    # CRITICAL FIX: Repair the private key's newlines
    if "private_key" in creds_dict:
        pk = creds_dict["private_key"]
        pk = pk.replace("\\n", "\n")
        pk = pk.replace("\r", "")
        if "-----BEGIN PRIVATE KEY-----" not in pk:
            raise RuntimeError("private_key is missing PEM header.")
        creds_dict["private_key"] = pk

    required = ["type", "project_id", "private_key_id", "private_key", "client_email"]
    for field in required:
        if field not in creds_dict:
            raise RuntimeError(f"Firebase credentials missing required field: {field}")

    cred = credentials.Certificate(creds_dict)
    firebase_admin.initialize_app(cred)
    print(f"✅ Firebase initialized for project: {creds_dict.get('project_id')}")


_init_firebase()


def send_notification(token: str, title: str, body: str, data: dict = None) -> bool:
    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    channel_id="fixnow_notifications",
                ),
            ),
        )
        messaging.send(message)
        return True
    except Exception as e:
        print(f"⚠️ FCM send failed: {e}")
        return False


def send_multicast_notification(tokens: list, title: str, body: str, data: dict = None) -> int:
    if not tokens:
        return 0
    try:
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            tokens=tokens,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    channel_id="fixnow_notifications",
                ),
            ),
        )
        response = messaging.send_each_for_multicast(message)
        return response.success_count
    except Exception as e:
        print(f"⚠️ FCM multicast failed: {e}")
        return 0
