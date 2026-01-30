from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.elasticsearch import router as es_router
from app.core.deps import initialize_dependencies
from app.core.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await initialize_dependencies()
        yield
    except Exception as e:
        print(f"Error initializing dependencies: {e}")
        raise e


app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {
        "message": "Welcome to the ELK Stack Backend",
        "available_routes": [
            f"{settings.API_PREFIX}/elasticsearch",
        ]
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(es_router, prefix=f"{settings.API_PREFIX}")

@app.get("/health")
async def health():
    return {"status": "healthy"}