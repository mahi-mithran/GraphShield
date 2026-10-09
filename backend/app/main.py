"""
GraphShield - FastAPI Application Entrypoint
Smart India Hackathon 2026 (SIH26199) - Team GraphSentinelz
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.core.db import init_db, seed_initial_data_if_empty
from backend.app.api.routes_risk import router as risk_router
from backend.app.api.routes_transactions import router as transactions_router
from backend.app.api.routes_graph import router as graph_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler:
    Initializes database tables and seeds initial transactions/entities on startup.
    """
    print("=" * 60)
    print("GraphShield Backend API Initializing...")
    print(f"Environment: {settings.ENV}")
    print(f"Database URL: {settings.DATABASE_URL}")
    print(f"Risk Thresholds: FRAUD >= {settings.RISK_THRESHOLD_FRAUD}, MID_LEVEL >= {settings.RISK_THRESHOLD_MID}, GENUINE < {settings.RISK_THRESHOLD_MID}")
    print("=" * 60)
    
    # Ensure processed directory exists
    os.makedirs(settings.PROCESSED_DATA_DIR, exist_ok=True)
    
    # Initialize DB tables
    init_db()
    
    # Seed transactions if database is fresh
    try:
        seed_initial_data_if_empty()
    except Exception as e:
        print(f"[Warning] Seeding skipped or encountered non-fatal error: {e}")
        
    yield
    print("GraphShield Backend API Shutting Down...")


app = FastAPI(
    title="GraphShield - Graph-Based Fraud Detection API",
    description=(
        "Smart India Hackathon 2026 (SIH26199) | Team GraphSentinelz\n\n"
        "Advanced Graph Neural Network (GraphSAGE) fraud detection system classifying "
        "transactions into exactly THREE tiers:\n"
        "- **FRAUD** (Risk Score >= 0.70)\n"
        "- **MID_LEVEL** (0.30 <= Risk Score < 0.70)\n"
        "- **GENUINE** (Risk Score < 0.30)"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for Streamlit frontend and local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(risk_router, prefix="/risk", tags=["Risk Engine"])
app.include_router(transactions_router, prefix="/transactions", tags=["Transactions & Feedback"])
app.include_router(graph_router, prefix="/graph", tags=["Graph Intelligence"])


@app.get("/", tags=["System"])
def root():
    """Root status endpoint."""
    return {
        "project": "GraphShield Fraud Detection System",
        "hackathon": "Smart India Hackathon 2026 (SIH26199)",
        "team": "GraphSentinelz",
        "status": "online",
        "documentation": "/docs",
        "risk_tiers": ["FRAUD", "MID_LEVEL", "GENUINE"],
    }


@app.get("/health", tags=["System"])
def health_check():
    """Comprehensive health check checking model file and database status."""
    model_exists = os.path.exists(settings.MODEL_CHECKPOINT_PATH)
    csv_exists = os.path.exists(settings.DATASET_CSV_PATH)
    return {
        "status": "healthy",
        "database": "connected",
        "gnn_model_loaded": model_exists,
        "dataset_ready": csv_exists,
        "risk_thresholds": {
            "FRAUD": f">= {settings.RISK_THRESHOLD_FRAUD}",
            "MID_LEVEL": f"{settings.RISK_THRESHOLD_MID} - {settings.RISK_THRESHOLD_FRAUD}",
            "GENUINE": f"< {settings.RISK_THRESHOLD_MID}",
        },
    }
