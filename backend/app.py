from fastapi import FastAPI
from routers import auth_router, users_router, categories_router, skills_router
from fastapi.middleware.cors import CORSMiddleware
from DB.database import Base, engine


app = FastAPI(title="Work Near API", description="Rent People To Do Work For You")

origins = [
    "http://localhost:3000", 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(categories_router)
app.include_router(skills_router)

@app.get("/")
async def index():
    return "Landing page"