@echo off
TITLE GraphShield - SIH26199 Team GraphSentinelz Launcher
echo ======================================================================
echo           GraphShield: Graph-Based Fraud Detection System
echo           Smart India Hackathon 2026 - Team GraphSentinelz
echo ======================================================================
echo.

cd /d "%~dp0"

REM Use the project's virtual environment if it exists
if exist "venv\Scripts\activate.bat" call "venv\Scripts\activate.bat"

REM Make the project root importable (backend.* and frontend.* imports)
set "PYTHONPATH=%~dp0"

echo [1/3] Checking dataset and GNN model...
REM Generates the dataset if missing (or replaces an old-format CSV; a backup is kept)
python -c "from backend.app.core.data_loader import ensure_dataset; ensure_dataset()"

if not exist "backend\data\processed\fraud_graphsage.pt" (
    echo GNN model checkpoint not found. Training GraphSAGE model...
    python -m backend.app.graph.train
    if errorlevel 1 echo [Warning] Training failed - the API will use the graph-heuristic fallback.
)

echo.
echo [2/3] Starting FastAPI Backend on http://127.0.0.1:8000 ...
REM Note: no --reload here, because the venv folder inside the project would be watched and slow everything down.
start "GraphShield Backend API (Port 8000)" cmd /k python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

echo Waiting 6 seconds for backend to initialize (first start seeds the database)...
timeout /t 6 /nobreak >nul

echo.
echo [3/3] Starting Streamlit Frontend on http://localhost:8501 ...
start "GraphShield Streamlit Dashboard (Port 8501)" cmd /k python -m streamlit run frontend\app.py --server.port 8501

echo.
echo ======================================================================
echo GraphShield is now launching!
echo Backend Docs:  http://127.0.0.1:8000/docs
echo Frontend URL:  http://localhost:8501
echo ======================================================================
pause
