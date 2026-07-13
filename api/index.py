"""Vercel serverless entry point for the FastAPI application."""

from fastapi import FastAPI

from app.main import app as portfolio_app


# Vercel preserves the browser's original path when a rewrite invokes this
# function. Mount the application at both paths so same-origin frontend calls
# and conventional /api/* calls share the same implementation.
app = FastAPI(title="Portfolio Risk Copilot - Vercel")
app.mount("/api", portfolio_app)
app.mount("/", portfolio_app)

__all__ = ["app"]
