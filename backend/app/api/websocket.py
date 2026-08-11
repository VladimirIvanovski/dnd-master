import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.database.models import Character
from app.database.session import SessionLocal
from app.schemas.gameplay import PlayerActionRequest
from app.services.gameplay import GameplayService
from app.api.security import require_character_access

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/gameplay")
async def gameplay_ws(websocket: WebSocket):
    await websocket.accept()
    username = websocket.query_params.get("username", "player")
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                request = PlayerActionRequest.model_validate_json(raw)
            except ValidationError as exc:
                await websocket.send_json(
                    {"type": "error", "detail": "invalid_request", "errors": exc.errors()}
                )
                continue

            await websocket.send_json({"type": "status", "message": "processing"})

            def _run():
                db = SessionLocal()
                try:
                    require_character_access(db, request.character_id, username)
                    character = db.get(Character, request.character_id)
                    if character is None or character.campaign_id != request.campaign_id:
                        raise ValueError("Character not in campaign")
                    service = GameplayService(db)
                    return service.handle_action(request).model_dump(mode="json")
                finally:
                    db.close()

            try:
                payload = await asyncio.to_thread(_run)
                narration = payload.get("narration", "")
                for i in range(0, len(narration), 48):
                    await websocket.send_json(
                        {"type": "narration_chunk", "text": narration[i : i + 48]}
                    )
                await websocket.send_json({"type": "result", "data": payload})
            except Exception as exc:  # noqa: BLE001
                detail = getattr(exc, "detail", None) or str(exc)
                if not isinstance(detail, str):
                    detail = "request failed"
                await websocket.send_json({"type": "error", "detail": detail})
    except WebSocketDisconnect:
        return
