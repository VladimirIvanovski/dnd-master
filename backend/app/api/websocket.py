import asyncio

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.api.security import require_character_access, user_from_token
from app.database.models import Character, User
from app.database.session import SessionLocal
from app.schemas.gameplay import PlayerActionRequest
from app.services.gameplay import GameplayService

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/gameplay")
async def gameplay_ws(websocket: WebSocket):
    token = websocket.query_params.get("token") or ""
    db = SessionLocal()
    try:
        try:
            user = user_from_token(db, token)
            user_id = user.id
        except HTTPException:
            await websocket.close(code=4401)
            return
    finally:
        db.close()

    await websocket.accept()
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
                session = SessionLocal()
                try:
                    current_user = session.get(User, user_id)
                    if current_user is None:
                        raise ValueError("User not found")
                    require_character_access(session, request.character_id, current_user)
                    character = session.get(Character, request.character_id)
                    if character is None or character.campaign_id != request.campaign_id:
                        raise ValueError("Character not in campaign")
                    service = GameplayService(session)
                    return service.handle_action(request).model_dump(mode="json")
                finally:
                    session.close()

            try:
                payload = await asyncio.to_thread(_run)
                narration = payload.get("narration", "")
                for i in range(0, len(narration), 48):
                    await websocket.send_json(
                        {"type": "narration_chunk", "text": narration[i : i + 48]}
                    )
                await websocket.send_json({"type": "result", "data": payload})
            except Exception as exc:  # noqa: BLE001
                from app.ai.fallback_provider import LLMUnavailableError, USER_LIMIT_MESSAGE

                if isinstance(exc, LLMUnavailableError):
                    detail = str(exc)
                else:
                    detail = getattr(exc, "detail", None) or str(exc)
                    if not isinstance(detail, str):
                        detail = "request failed"
                    low = detail.lower()
                    if any(
                        x in low
                        for x in ("429", "402", "404", "rate limit", "too many requests", "payment required")
                    ):
                        detail = USER_LIMIT_MESSAGE
                await websocket.send_json({"type": "error", "detail": detail})
    except WebSocketDisconnect:
        return
