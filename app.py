from fastapi import FastAPI
from routers import auth_router
from DB.database import Base, engine


app = FastAPI(title="Work Near API", description="Rent People To Do Work For You")

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app.include_router(auth_router)


@app.get("/")
async def index():
    return "Landing page"