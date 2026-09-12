from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import json
import os
from jose import JWTError, jwt

from ..database import get_db
from .. import models, schemas

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)

SECRET_KEY = os.getenv("SECRET_KEY", "fixnow_secret_key_2024")
ALGORITHM = "HS256"
security = HTTPBearer()


def get_sender_info(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        token_type = payload.get("type")

        if token_type == "customer":
            user = db.query(models.User).filter(models.User.id == user_id).first()
            return {
                "id": user_id,
                "type": "customer",
                "name": user.name if user else "Customer",
                "booking_owner": True,
            }
        elif token_type == "mechanic":
            mechanic = db.query(models.Mechanic).filter(models.Mechanic.id == user_id).first()
            return {
                "id": user_id,
                "type": "mechanic",
                "name": mechanic.name if mechanic else "Mechanic",
                "booking_owner": False,
            }
    except JWTError:
        pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, booking_id: int, websocket: WebSocket):
        await websocket.accept()
        if booking_id not in self.active_connections:
            self.active_connections[booking_id] = []
        self.active_connections[booking_id].append(websocket)

    def disconnect(self, booking_id: int, websocket: WebSocket):
        if booking_id in self.active_connections:
            if websocket in self.active_connections[booking_id]:
                self.active_connections[booking_id].remove(websocket)
            if len(self.active_connections[booking_id]) == 0:
                del self.active_connections[booking_id]

    async def broadcast(self, booking_id: int, message: dict):
        if booking_id in self.active_connections:
            for connection in self.active_connections[booking_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass


manager = ConnectionManager()


@router.get("/{booking_id}", response_model=List[schemas.MessageResponse])
def get_messages(
    booking_id: int,
    db: Session = Depends(get_db),
    sender: dict = Depends(get_sender_info),
):
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
    ).first()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    messages = db.query(models.Message).filter(
        models.Message.booking_id == booking_id
    ).order_by(models.Message.created_at.asc()).all()

    return messages


@router.post("/{booking_id}", response_model=schemas.MessageResponse, status_code=status.HTTP_201_CREATED)
def send_message(
    booking_id: int,
    message_data: schemas.MessageCreate,
    db: Session = Depends(get_db),
    sender: dict = Depends(get_sender_info),
):
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
    ).first()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    new_message = models.Message(
        booking_id=booking_id,
        sender_type=sender["type"],
        sender_name=sender["name"],
        content=message_data.content,
    )

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    import asyncio
    try:
        asyncio.create_task(manager.broadcast(booking_id, {
            "id": new_message.id,
            "booking_id": new_message.booking_id,
            "sender_type": new_message.sender_type,
            "sender_name": new_message.sender_name,
            "content": new_message.content,
            "created_at": new_message.created_at.isoformat(),
        }))
    except Exception:
        pass

    return new_message


@router.websocket("/ws/{booking_id}")
async def websocket_chat(websocket: WebSocket, booking_id: int):
    await manager.connect(booking_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()

            db = next(get_db())
            try:
                new_message = models.Message(
                    booking_id=booking_id,
                    sender_type=data.get("sender_type", "customer"),
                    sender_name=data.get("sender_name", "Customer"),
                    content=data.get("content", ""),
                )

                db.add(new_message)
                db.commit()
                db.refresh(new_message)

                await manager.broadcast(booking_id, {
                    "id": new_message.id,
                    "booking_id": new_message.booking_id,
                    "sender_type": new_message.sender_type,
                    "sender_name": new_message.sender_name,
                    "content": new_message.content,
                    "created_at": new_message.created_at.isoformat(),
                })
            finally:
                db.close()

    except WebSocketDisconnect:
        manager.disconnect(booking_id, websocket)
    except Exception:
        manager.disconnect(booking_id, websocket)