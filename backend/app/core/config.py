"""
GraphShield - Application Configuration
Smart India Hackathon 2026 (SIH26199) - Team GraphSentinelz
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent   # .../backend
PROJECT_ROOT = BASE_DIR.parent                             # project root (contains backend/ and frontend/)
load_dotenv(BASE_DIR / ".env")


def _resolve_database_url(url: str) -> str:
    """
    Turn a relative SQLite path (e.g. sqlite:///./backend/data/processed/graphshield.db) into an absolute one.
    Otherwise the API would silently create a brand-new, empty database whenever it is started
    from a folder other than the project root.
    """
    prefix = "sqlite:///"
    if url.startswith(prefix):
        raw_path = url[len(prefix):]
        if raw_path and raw_path != ":memory:" and not Path(raw_path).is_absolute():
            return f"{prefix}{(PROJECT_ROOT / raw_path).resolve().as_posix()}"
    return url


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "GraphShield Fraud Detection API")
    ENV: str = os.getenv("ENV", "development")
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", 8000))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1")

    # Project Directories
    BACKEND_DIR: Path = BASE_DIR
    RAW_DATA_DIR: Path = BASE_DIR / "data" / "raw"
    PROCESSED_DATA_DIR: Path = BASE_DIR / "data" / "processed"

    # SQLite zero-setup database file path (resolved absolute path)
    DB_FILE_PATH: Path = PROCESSED_DATA_DIR / "graphshield.db"
    DATABASE_URL: str = _resolve_database_url(
        os.getenv(
            "DATABASE_URL",
            f"sqlite:///{DB_FILE_PATH.as_posix()}",
        )
    )

    # Machine Learning and Dataset Paths
    DATASET_CSV_PATH: Path = PROCESSED_DATA_DIR / "transactions_labeled.csv"
    RAW_DATASET_CSV_PATH: Path = RAW_DATA_DIR / "transactions_labeled.csv"
    MODEL_CHECKPOINT_PATH: Path = PROCESSED_DATA_DIR / "fraud_graphsage.pt"
    MODEL_METADATA_PATH: Path = PROCESSED_DATA_DIR / "model_metadata.json"

    # MANDATORY THREE-TIER RISK CLASSIFICATION THRESHOLDS
    # risk_score >= 0.70         -> "FRAUD"
    # 0.30 <= risk_score < 0.70  -> "MID_LEVEL"
    # risk_score < 0.30          -> "GENUINE"
    RISK_THRESHOLD_FRAUD: float = float(os.getenv("RISK_THRESHOLD_FRAUD", 0.70))
    RISK_THRESHOLD_MID: float = float(os.getenv("RISK_THRESHOLD_MID", 0.30))

    TIER_FRAUD: str = "FRAUD"
    TIER_MID_LEVEL: str = "MID_LEVEL"
    TIER_GENUINE: str = "GENUINE"

    # CORS origins
    CORS_ORIGINS: list = ["*"]


settings = Settings()
