from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth
from app.auth.dependencies import get_current_user

app = FastAPI(title="Smart BOE")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/dashboard/ping")
def dashboard_ping(current_user: str = Depends(get_current_user)):
    return {"message": f"Hello {current_user}, you are authenticated."}