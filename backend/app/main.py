print("A: Starting main.py", flush=True)

from fastapi import FastAPI, Depends
print("B: FastAPI imported", flush=True)

from fastapi.middleware.cors import CORSMiddleware
print("C: CORS imported", flush=True)

from app.routers import auth, papers
print("D: Routers imported", flush=True)

from app.auth.dependencies import get_current_user
print("E: Auth dependencies imported", flush=True)

from app.database import init_db
print("F: Database imported", flush=True)

from app.config import ALLOWED_ORIGINS_LIST
print("G: Config imported", flush=True)
app = FastAPI(title="Smart BOE")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(papers.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/dashboard/ping")
def dashboard_ping(current_user: str = Depends(get_current_user)):
    return {"message": f"Hello {current_user}, you are authenticated."}