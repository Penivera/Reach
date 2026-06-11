from fastapi import FastAPI
from routers import auth_router

app = FastAPI(title="Work Near API", description="Rent People To Do Work For You")

app.include_router(auth_router)


