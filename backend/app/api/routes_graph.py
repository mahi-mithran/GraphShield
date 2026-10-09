"""
GraphShield - Graph Intelligence API Routes
GET /graph/{entity_id} -> Retrieves REAL relationship graph data from the database/graph.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from backend.app.core.db import get_db
from backend.app.graph.build_graph import get_entity_subgraph_data

router = APIRouter()


@router.get(
    "/{entity_id}",
    summary="Get real relationship subgraph for an entity (Account, Device, IP, Merchant, Transaction)",
)
def get_entity_graph(
    entity_id: str,
    depth: int = Query(2, ge=1, le=3, description="Graph traversal depth (1 or 2 hops recommended)"),
    max_neighbors: int = Query(60, ge=5, le=200, description="Max neighbor nodes to prevent browser freeze"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Extracts real relational links centered around entity_id from SQLite DB transactions.
    Constructs a multi-entity graph linking Accounts, Transactions, Devices, IPs, and Merchants.
    """
    clean_id = entity_id.strip()
    if not clean_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Entity ID cannot be empty.")

    subgraph = get_entity_subgraph_data(
        entity_id=clean_id,
        depth=depth,
        max_neighbors=max_neighbors,
        db=db,
    )

    if not subgraph or not subgraph.get("nodes"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{clean_id}' was not found in active transactions or graph database.",
        )

    return subgraph
