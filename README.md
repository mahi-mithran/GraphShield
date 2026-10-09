# GraphShield: Graph-Based Fraud Detection System

**Smart India Hackathon 2026 (SIH26199)**  
**Team: GraphSentinelz**  

GraphShield is an end-to-end graph neural network (GNN) fraud detection system engineered for financial transaction monitoring. It maps relationships across accounts, devices, IP addresses, merchants, and payment methods into a heterogeneous entity-relationship graph, leverages a **GraphSAGE** (PyTorch Geometric) architecture to detect fraud rings and syndicated financial crime, and delivers explainable decisions via **GNNExplainer**.

---

## 🎯 3-Tier Classification Decision Rules

GraphShield enforces a strict three-tier classification architecture across the entire stack (FastAPI backend, SQLite/SQLAlchemy database, and Streamlit dashboard):

| Decision Tier | Score Threshold | Action / Meaning | Color Indicator |
| :--- | :--- | :--- | :--- |
| **`FRAUD`** | `risk_score >= 0.70` | High Risk: Instantly block transaction, trigger alert | 🔴 Red |
| **`MID_LEVEL`** | `0.30 <= risk_score < 0.70` | Medium Risk: Step-up verification (2FA/OTP/Analyst Review) | 🟠 Orange |
| **`GENUINE`** | `risk_score < 0.30` | Low Risk: Allow transaction automatically | 🟢 Green |

---

## 🧱 Architecture & Tech Stack

```mermaid
flowchart TD
    subgraph Data Layer
        GEN[generate_dataset.py] -->|~5000 Transactions with Fraud Rings| CSV[(transactions_labeled.csv)]
        CSV -->|Seeds / Ingests| DB[(SQLite: graphshield.db)]
    end

    subgraph Machine Learning Layer
        CSV -->|Build Graph| GRAPH[NetworkX Multi-Entity Graph]
        GRAPH -->|PyG Data Loader| SAGE[FraudGraphSAGE Model]
        SAGE -->|Train & Checkpoint| PT[(fraud_graphsage.pt)]
        PT -->|Inference + Explainability| EXPLAIN[GNNExplainer Engine]
    end

    subgraph Backend API [FastAPI - Port 8000]
        API_RISK[POST /risk/predict] -->|Persists & Scores| DB
        API_TX[GET /transactions] --> DB
        API_FLAG[GET /transactions/flagged] --> DB
        API_FEED[POST /transactions/feedback] --> DB
        API_GRAPH[GET /graph/{entity_id}] --> GRAPH
        EXPLAIN --> API_RISK
    end

    subgraph Frontend [Streamlit - Port 8501]
        P1[1_Dashboard] -->|KPIs, Tiers, Sector Distribution| Backend
        P2[2_Transaction_Check] -->|Submit Real-Time Check & Explanations| Backend
        P3[3_Graph_Explorer] -->|Interactive Pyvis Ring Visualization| Backend
        P4[4_Analyst_Review] -->|Confirm / Verify / Reject Actions| Backend
    end
```

- **Backend**: FastAPI, SQLAlchemy, SQLite, PyTorch, PyTorch Geometric (GraphSAGE), GNNExplainer
- **Frontend**: Streamlit multi-page application, Pyvis for interactive entity graphs
- **Data Generator**: Synthetic Kaggle-style financial transaction generator with syndicated device/IP fraud rings

---

## 📁 Repository Structure

```
graphshield/
├── requirements.txt
├── README.md
├── start_all.bat
├── backend/
│   ├── .env.example
│   ├── app/
│   │   ├── main.py                    (FastAPI app, CORS, routers, DB init on startup)
│   │   ├── api/
│   │   │   ├── routes_risk.py         (POST /risk/predict -> runs model, saves to DB, returns 3 tiers)
│   │   │   ├── routes_transactions.py (GET /transactions/, GET /transactions/flagged, POST feedback)
│   │   │   └── routes_graph.py        (GET /graph/{entity_id} -> real entity-relationship graph)
│   │   ├── core/
│   │   │   ├── config.py              (Settings, DB config, risk thresholds for 3 tiers)
│   │   │   └── db.py                  (SQLAlchemy engine, session, init_db, auto-seeder)
│   │   ├── models/
│   │   │   ├── db_models.py           (User, Account, Device, Merchant, PaymentMethod, Transaction, AnalystFeedback)
│   │   │   └── schema.py              (Pydantic request/response validation schemas)
│   │   ├── graph/
│   │   │   ├── build_graph.py         (NetworkX graph builder for heterogeneous relationships)
│   │   │   ├── gnn_model.py           (FraudGraphSAGE: 2-layer SAGEConv + classifier)
│   │   │   ├── train.py               (trains on synthetic CSV, saves checkpoint .pt)
│   │   │   └── explain.py             (GNNExplainer wrapper -> plain-language reasons)
│   │   └── services/
│   │       ├── risk_engine.py         (decide() function: FRAUD/MID_LEVEL/GENUINE + mock fallback)
│   │       └── feedback.py            (persists analyst feedback & updates audit status)
│   └── data/
│       ├── raw/
│       │   └── generate_dataset.py    (synthetic generator with 8% fraud rings sharing devices/IPs)
│       └── processed/                 (stores transactions_labeled.csv, graphshield.db, fraud_graphsage.pt)
└── frontend/
    ├── app.py                          (Streamlit entrypoint, sidebar status & overview)
    ├── components/
    │   ├── api_client.py               (HTTP client wrapper with graceful connection error handling)
    │   └── graph_viz.py                (Pyvis interactive graph component with color-coded nodes)
    └── pages/
        ├── 0_Live_Payment_Gateway.py    (Checkout demo: Allow / Step-Up / Block scenarios)
        ├── 1_Dashboard.py              (KPI cards, 3-tier distribution, sector chart, recent transactions)
        ├── 2_Transaction_Check.py       (Real-time submission, risk score badge, explainability bullets)
        ├── 3_Graph_Explorer.py          (Interactive graph of entity neighborhoods: accounts, devices, IPs)
        └── 4_Analyst_Review.py          (Actionable queue for FRAUD & MID_LEVEL alerts)
```

---

## 🚀 Quickstart Guide (Windows Terminal)

Follow these exact steps to set up and run GraphShield on your local machine:

### 1. Prerequisites & Environment Setup
Open PowerShell or Command Prompt in the project folder:
```powershell
# Navigate into the graphshield directory
cd path\to\graphshieldn1

# Create a Python virtual environment
python -m venv venv

# Activate the virtual environment
.\venv\Scripts\activate

# Install all required dependencies
pip install -r requirements.txt
```

### 2. Generate Synthetic Dataset
Generate ~5,000 transactions featuring realistic fraud rings (device & IP sharing across multiple accounts):
```powershell
python -m backend.data.raw.generate_dataset
```
*Output: Generates `backend\data\processed\transactions_labeled.csv`.*

### 3. Train the GraphSAGE GNN Model
Train the 2-layer GraphSAGE fraud classifier:
```powershell
python -m backend.app.graph.train
```
*Output: Trains with PyTorch Geometric, prints Epoch losses and test accuracy, and exports `backend\data\processed\fraud_graphsage.pt`.*

### 4. Option A: Launch Both Services with One Click
Run the included batch script:
```cmd
start_all.bat
```
This opens two independent terminal windows:
- **Backend API**: Running on `http://127.0.0.1:8000` (Swagger docs: `http://127.0.0.1:8000/docs`)
- **Frontend Dashboard**: Running on `http://localhost:8501`

### 4. Option B: Launch Services Manually in Separate Terminals

**Terminal 1 (Backend FastAPI):**
```powershell
cd path\to\graphshieldn1
.\venv\Scripts\activate
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 (Frontend Streamlit):**
```powershell
cd path\to\graphshieldn1
.\venv\Scripts\activate
python -m streamlit run frontend\app.py --server.port 8501
```

---

## 🔍 How to Confirm It's Working

1. **Verify Backend Health**:
   - Open `http://127.0.0.1:8000/docs` in your browser.
   - Execute `GET /health` or `GET /transactions/`. You will see seeded transactions and model status.

2. **Open the Dashboard**:
   - Open `http://localhost:8501` in your browser.
   - Check the sidebar: Backend status should be green **Connected**.
   - Navigate to **`1_Dashboard`**: Notice the KPI metrics for Total Transactions, percentages and counts for **FRAUD**, **MID_LEVEL**, and **GENUINE**, the sector breakdown, and the color-coded transaction table.

3. **Test Real-Time Prediction**:
   - Navigate to **`2_Transaction_Check`**.
   - Select a pre-loaded scenario (e.g., *Fraud Ring Device Reuse* or *Suspicious Velocity Spike*).
   - Click **Run GraphShield Risk Analysis**.
   - Review the risk score, the prominent badge (`FRAUD` / `MID_LEVEL` / `GENUINE`), and the GNNExplainer graph reasoning points.

4. **Explore the Relationship Graph**:
   - Navigate to **`3_Graph_Explorer`**.
   - Enter an entity ID (e.g., `ACC-FRAUD-RING-01-1` or `DEV-FRAUD-RING-01`).
   - Click **Explore Entity Graph** to view the interactive Pyvis graph showing how multiple accounts cluster around the same device and IP.

5. **Review and Resolve Alerts**:
   - Navigate to **`4_Analyst_Review`**.
   - Review flagged `FRAUD` and `MID_LEVEL` transactions.
   - Click **Confirm Fraud**, **Verify User**, or **Reject Alert**. The status updates live in the database and audit trail!
