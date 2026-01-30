
from fastapi import APIRouter, Depends, HTTPException, Request
from datetime import datetime
from ..database import announcements_collection
from pymongo.collection import ReturnDocument
from ..database import announcements_collection
from pymongo.collection import ReturnDocument

router = APIRouter(prefix="/announcements", tags=["announcements"])

# Authentication dependency: relies on user being set in request.state by auth middleware
def get_current_user(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        # No authenticated user found; reject the request
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user

@router.get("/")
def list_announcements(user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    anns = list(announcements_collection.find({}))
    for ann in anns:
        ann["_id"] = str(ann["_id"])
        # Convert datetime to isoformat for frontend
        if "start_date" in ann and ann["start_date"]:
            ann["start_date"] = ann["start_date"].isoformat()
        if "expiration_date" in ann and ann["expiration_date"]:
            ann["expiration_date"] = ann["expiration_date"].isoformat()
    return anns

@router.post("/", status_code=201)
def create_announcement(announcement: dict, user: dict = Depends(get_current_user)):
    if not user or user.get("role") not in ("admin", "teacher"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    # Validate required fields
    if not announcement.get("title") or not announcement.get("message") or not announcement.get("expiration_date"):
        raise HTTPException(status_code=400, detail="Title, message, and expiration date are required.")
    # Parse dates
    if announcement.get("start_date"):
        try:
            announcement["start_date"] = datetime.fromisoformat(announcement["start_date"])
        except Exception:
            announcement["start_date"] = None
    try:
        announcement["expiration_date"] = datetime.fromisoformat(announcement["expiration_date"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid expiration date format.")
    announcement["created_by"] = user["username"]
    announcement["created_at"] = datetime.now()
    announcement["last_modified"] = datetime.now()
    result = announcements_collection.insert_one(announcement)
    announcement["_id"] = str(result.inserted_id)
    return announcement

@router.put("/{announcement_id}")
def update_announcement(announcement_id: str, update: dict, user: dict = Depends(get_current_user)):
    if not user or user.get("role") not in ("admin", "teacher"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    update["last_modified"] = datetime.now()
    # Parse dates
    if update.get("start_date"):
        try:
            update["start_date"] = datetime.fromisoformat(update["start_date"])
        except Exception:
            update["start_date"] = None
    if update.get("expiration_date"):
        try:
            update["expiration_date"] = datetime.fromisoformat(update["expiration_date"])
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid expiration date format.")
    ann = announcements_collection.find_one_and_update(
        {"_id": announcement_id},
        {"$set": update},
        return_document=ReturnDocument.AFTER
    )
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    ann["_id"] = str(ann["_id"])
    if "start_date" in ann and ann["start_date"]:
        ann["start_date"] = ann["start_date"].isoformat()
    if "expiration_date" in ann and ann["expiration_date"]:
        ann["expiration_date"] = ann["expiration_date"].isoformat()
    return ann

@router.delete("/{announcement_id}", status_code=204)
def delete_announcement(announcement_id: str, user: dict = Depends(get_current_user)):
    if not user or user.get("role") not in ("admin", "teacher"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = announcements_collection.delete_one({"_id": announcement_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return
