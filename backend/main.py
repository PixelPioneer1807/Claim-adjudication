from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

from app.config import settings
from app.database import engine, Base
from app.routes import router
from app.policy_loader import load_policy_terms
from app.adjudication_engine import initialize_engine

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="OPD Claim Adjudication API",
    description="AI-powered automated insurance claim processing system",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load policy terms and initialize adjudication engine
policy_terms = load_policy_terms()
initialize_engine(policy_terms)

# Include routers
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    print("\n" + "=" * 60)
    print("🚀 OPD Claim Adjudication API Starting...")
    print("=" * 60)

    # Create upload directory if not exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    print(f"✅ Upload directory: {settings.UPLOAD_DIR}")

    print(f"✅ Database: {settings.DATABASE_URL}")
    print(f"✅ AI Model: {settings.AI_MODEL}")
    print(f"✅ Policy loaded: {policy_terms.get('policy_name', 'Unknown')}")
    print("=" * 60 + "\n")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "OPD Claim Adjudication API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    print(f"❌ Unhandled exception: {str(exc)}")
    import traceback

    traceback.print_exc()

    return JSONResponse(
        status_code=500, content={"error": "Internal server error", "detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
