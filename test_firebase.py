import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, messaging

b64 = os.getenv("FIREBASE_CREDENTIALS_B64")
if not b64:
    # Fall back to reading file directly
    creds_dict = json.load(open("firebase-service-account.json"))
else:
    creds_dict = json.loads(base64.b64decode(b64).decode())

print("project_id:", creds_dict.get("project_id"))
print("client_email:", creds_dict.get("client_email"))
print("private_key_id:", creds_dict.get("private_key_id"))
print("private_key starts with:", creds_dict.get("private_key", "")[:40])
print("private_key ends with:", creds_dict.get("private_key", "")[-40:])

cred = credentials.Certificate(creds_dict)
app = firebase_admin.initialize_app(cred)

try:
    message = messaging.Message(
        notification=messaging.Notification(title="Test", body="Test"),
        token="dummy_token_that_will_fail",
    )
    messaging.send(message)
    print("SENT (unexpected)")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
