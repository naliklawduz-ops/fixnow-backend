from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Dict
import json

from ..database import get_db
from .. import models, schemas
from ..auth_utils import get_current_user_id

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
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
    user_id: int = Depends(get_current_user_id),
):
    """Get all messages for a booking."""
    
    # Verify booking exists and belongs to user
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.user_id == user_id,
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
    user_id: int = Depends(get_current_user_id),
):
    """Send a message for a booking."""
    
    # Verify booking exists and belongs to user
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.user_id == user_id,
    ).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Get user name
    user = db.query(models.User).filter(models.User.id == user_id).first()
    
    new_message = models.Message(
        booking_id=booking_id,
        sender_type="customer",
        sender_name=user.name if user else "Customer",
        content=message_data.content,
    )
    
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
    # Broadcast to WebSocket connections
    import asyncio
    asyncio.create_task(manager.broadcast(booking_id, {
        "id": new_message.id,
        "booking_id": new_message.booking_id,
        "sender_type": new_message.sender_type,
        "sender_name": new_message.sender_name,
        "content": new_message.content,
        "created_at": new_message.created_at.isoformat(),
    }))
    
    return new_message


@router.websocket("/ws/{booking_id}")
async def websocket_chat(websocket: WebSocket, booking_id: int):
    """WebSocket endpoint for real-time chat."""
    
    await manager.connect(booking_id, websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Save to database
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
                
                # Broadcast to all connections
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
    except Exception as e:
        manager.disconnect(booking_id, websocket)