from fastapi import APIRouter, Depends

from auth import get_current_user
from db import get_db
from utils import paginate

router = APIRouter(prefix="/api/activity-logs", tags=["activity"])


@router.get("")
async def list_logs(q: str = "", module: str = "", user_id: str = "", page: int = 1, per_page: int = 30, user: dict = Depends(get_current_user)):
    db = get_db()
    query: dict = {}
    if q:
        query["$or"] = [
            {"user_email": {"$regex": q, "$options": "i"}},
            {"details": {"$regex": q, "$options": "i"}},
            {"action": {"$regex": q, "$options": "i"}},
        ]
    if module:
        query["module"] = module
    if user_id:
        query["user_id"] = user_id
    docs = await db.activity_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(20000)
    return paginate(docs, page, per_page)
