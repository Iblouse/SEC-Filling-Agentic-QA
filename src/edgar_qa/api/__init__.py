"""FastAPI service boundary for SEC filing agentic question answering."""

from edgar_qa.api.app import app, create_app

__all__ = ["app", "create_app"]
