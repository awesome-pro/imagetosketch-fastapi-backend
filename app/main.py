from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.database.connection import close_redis_client
from app.routers import auth, upload, sketch, websocket
import psutil

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    await close_redis_client()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
    # docs_url="/docs"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Image to Sketch API", "version": settings.app_version}
    
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": settings.app_version,
        "memory": psutil.virtual_memory().percent,
        "cpu": psutil.cpu_percent(),
        "disk": psutil.disk_usage("/").percent,
        "uptime": psutil.boot_time()
    }

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(sketch.router, prefix="/api")
app.include_router(websocket.router)
