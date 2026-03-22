# URL Shortener

Production-style URL shortener built with **FastAPI**, **CockroachDB**, and **DragonflyDB**.

## Architecture
```
Client
  ↓
FastAPI (:8000)
  ↓
SlowAPI Rate Limiting
  ↓
DragonflyDB Cache (Redis-compatible)
  ↓
CockroachDB Database
```

## Features
- Base62 short code generation from DB ID
- Custom aliases
- Expiring links
- Click counter analytics
- DragonflyDB caching with dynamic TTL
- IP-based rate limiting
- Input validation with Pydantic v2
- Structured logging

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/shorten` | Create a short URL |
| GET | `/api/v1/r/{short_code}` | Redirect to original URL |
| GET | `/api/v1/stats/{short_code}` | Get click analytics |
| GET | `/health` | Health check |

## Quick Start
```bash
# Copy environment file
cp .env.example .env

# Start all services
docker-compose up --build

# API available at http://localhost:8000
# CockroachDB UI at http://localhost:8080
# Docs at http://localhost:8000/docs
```

## Running Tests

Tests use SQLite in-memory — no external services needed.
```bash
pip install -r requirements.txt
pytest
```

## Project Structure
```
app/
├── main.py                      # FastAPI app factory
├── api/v1/endpoints/            # Route handlers
├── core/                        # Config, logging, rate limiting
├── db/                          # SQLAlchemy engine and session
├── models/                      # ORM models
├── schemas/                     # Pydantic schemas
├── services/                    # Business logic
└── utils/                       # Base62, network utilities
tests/                           # 49 tests, all passing
migrations/                      # Alembic migrations
docker/                          # Dockerfile
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI |
| Database | CockroachDB |
| Cache | DragonflyDB |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Rate Limiting | SlowAPI |
| Validation | Pydantic v2 |
| Testing | Pytest + TestClient |
| Container | Docker + Compose |