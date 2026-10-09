"""
GraphShield - Streamlit API Client Wrapper
Handles all HTTP requests to FastAPI backend with graceful connection error management.
"""

import os
import requests
import streamlit as st
from typing import Optional, Dict, Any, List, Tuple

BACKEND_BASE_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
CONNECTION_ERROR_MESSAGE = "Could not reach backend API. Is it running?"


class GraphShieldAPIClient:
    def __init__(self, base_url: str = BACKEND_BASE_URL):
        self.base_url = base_url

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, timeout: int = 6) -> Tuple[Optional[Any], Optional[str]]:
        url = f"{self.base_url}{endpoint}"
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code == 200:
                return resp.json(), None
            else:
                return None, f"API Error ({resp.status_code}): {resp.text}"
        except requests.exceptions.RequestException:
            return None, CONNECTION_ERROR_MESSAGE

    def _post(self, endpoint: str, json_data: Dict[str, Any], timeout: int = 10) -> Tuple[Optional[Any], Optional[str]]:
        url = f"{self.base_url}{endpoint}"
        try:
            resp = requests.post(url, json=json_data, timeout=timeout)
            if resp.status_code in (200, 201):
                return resp.json(), None
            else:
                return None, f"API Error ({resp.status_code}): {resp.text}"
        except requests.exceptions.RequestException:
            return None, CONNECTION_ERROR_MESSAGE

    def check_health(self) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        return self._get("/health", timeout=3)

    def get_dashboard_stats(self) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        return self._get("/transactions/stats")

    def get_transactions(
        self,
        skip: int = 0,
        limit: int = 50,
        decision: Optional[str] = None,
        sector: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        params = {"skip": skip, "limit": limit}
        if decision:
            params["decision"] = decision
        if sector:
            params["sector"] = sector
        if status:
            params["status"] = status
        return self._get("/transactions/", params=params)

    def get_flagged_transactions(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        params = {"skip": skip, "limit": limit}
        if status:
            params["status"] = status
        return self._get("/transactions/flagged", params=params)

    def predict_risk(self, payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        return self._post("/risk/predict", json_data=payload)

    def submit_feedback(self, payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        return self._post("/transactions/feedback", json_data=payload)

    def get_graph(self, entity_id: str, depth: int = 2, max_neighbors: int = 60) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        return self._get(f"/graph/{entity_id}", params={"depth": depth, "max_neighbors": max_neighbors})


api_client = GraphShieldAPIClient()


def render_api_error_if_any(error_msg: Optional[str]) -> bool:
    """Renders user-friendly error alert if backend is unreachable."""
    if error_msg:
        if error_msg == CONNECTION_ERROR_MESSAGE:
            st.error(f"⚠️ **{CONNECTION_ERROR_MESSAGE}**\n\nPlease ensure FastAPI is running at `{BACKEND_BASE_URL}`.")
        else:
            st.error(f"❌ {error_msg}")
        return True
    return False
