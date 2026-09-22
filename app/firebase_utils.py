import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, messaging
from dotenv import load_dotenv

load_dotenv()

_firebase_initialized = False

def _init_firebase():
    global _firebase_initialized
    if _firebase_initialized:
        return
    try:
        # Try base64-encoded JSON from environment variable (Railway)
        cred_b64 = os.getenv("FIREBASE_CREDENTIALS_B64")
        if cred_b64:
            cred_dict = json.loads(base64.b64decode(cred_b64).decode('utf-8'))
            cred = credentials.Certificate(cred_dict)
        else:
            # Try raw JSON from environment variable
            cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
            if cred_json:
                cred_dict = json.loads(cred_json)
                cred = credentials.Certificate(cred_dict)
            else:
                # Fall back to file path (local)
                cred_path = os.getenv("FIREBASE_CREDENTIALS", "firebase-service-account.json")
                if not os.path.isabs(cred_path):
                    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    cred_path = os.path.join(base_dir, cred_path)
                cred = credentials.Certificate(cred_path)

        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        print("✅ Firebase Admin SDK initialized")
    except Exception as e:
        print(f"⚠️ Firebase init failed: {e}")


def send_notification(token: str, title: str, body: str, data: dict = None) -> bool:
    _init_firebase()
    if not _firebase_initialized:
        return False
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
    _init_firebase()
    if not _firebase_initialized or not tokens:
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
