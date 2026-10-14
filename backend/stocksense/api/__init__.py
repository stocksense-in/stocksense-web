"""
StockSense REST API (FastAPI). Read-only over the data the pipeline writes,
plus live news and the prospectus scanner.

    uvicorn stocksense.api:app --reload          # http://localhost:8000/docs
"""

from .app import app, create_app

__all__ = ["app", "create_app"]
