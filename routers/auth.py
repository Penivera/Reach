from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/create_user")
async def create_user():
    pass

@router.post("/login")
async def login():
    pass

@router.post("/forgot_password")
async def forgot_password():
    pass

@router.post("/reset_password")
async def reset_password():
    pass

