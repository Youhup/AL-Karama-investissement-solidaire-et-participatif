from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import admin, auth, chat, documents, investments, projects, refunds, sectors

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # URL du front React (Vite)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(documents.router)
app.include_router(investments.router)
app.include_router(refunds.router)
app.include_router(sectors.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
