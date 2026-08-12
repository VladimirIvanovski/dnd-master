from fastapi import APIRouter

from app.api import auth, assets, campaigns, characters, gameplay, inventory, quests, websocket

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/api")
api_router.include_router(campaigns.router, prefix="/api")
api_router.include_router(characters.router, prefix="/api")
api_router.include_router(gameplay.router, prefix="/api")
api_router.include_router(inventory.router, prefix="/api")
api_router.include_router(quests.router, prefix="/api")
api_router.include_router(assets.router)
api_router.include_router(websocket.router)
