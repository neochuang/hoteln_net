# Grand Hilai Check-in System - CLAUDE.md

## Build & Run Commands
### Docker (Recommended)
- `docker compose up -d`: Start all services (PostgreSQL, Backend, Frontend)
- `docker compose up -d --build`: Rebuild and start
- `docker compose exec backend alembic upgrade head`: Run DB migrations
- `docker compose exec backend python -m app.seed`: Seed initial data (Local Dev Only)

### Local Development
- **Backend**:
  - `cd backend && python -m venv .venv && source .venv/bin/activate`
  - `pip install -e ".[dev]"`
  - `alembic upgrade head`
  - `python -m app.seed` (Warning: See script notes)
  - `uvicorn app.main:app --reload`
- **Frontend**:
  - `cd frontend && npm install`
  - `npm run dev`

## Test Commands
- **Backend**: `cd backend && pytest`
- **Frontend**: `cd frontend && npm run build` (Type checking via `vue-tsc`)

## Core Endpoints
- **Health Check**: `GET /api/health`
- **API Docs**: `GET /docs` (Swagger UI)

## Environment Variables
- `DATABASE_URL`: SQLAlchemy-compatible database URI (e.g., `postgresql+asyncpg://...`)
- `JWT_SECRET`: Secret key for signing tokens
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: Access token TTL
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS`: Refresh token TTL

## Coding Standards & Conventions
### Backend (FastAPI + SQLAlchemy 2.0)
- **Async Everything**: Use `async def` for routes and `await` for DB operations.
- **SQLAlchemy 2.0**: Use `Mapped` and `mapped_column` type hints.
- **Pydantic v2**: Use Pydantic models for request/response validation.
- **UUID**: All primary keys must be `UUID` (using `uuid4`).
- **Dependency Injection**: Use `Depends(get_db)` for database sessions.
- **Auth**: Use `Depends(get_current_user)` or `Depends(require_role(...))`.
- **Migrations**: Always use Alembic for schema changes.
- **Lifespan**: Use the `lifespan` context manager in `app/main.py` for startup/shutdown logic.

### Frontend (Vue 3 + TypeScript)
- **Composition API**: Use `<script setup>` syntax.
- **State Management**: Use Pinia (`stores/`).
- **API Client**: Use the shared axios client in `src/api/client.ts`.
- **Typing**: Define TypeScript interfaces in `src/types/index.ts`.
- **Auth Guard**: Protected routes should have `meta: { roles: [...] }` or `meta: { adminOnly: true }`.

## Project Structure
- `backend/app/models/`: SQLAlchemy ORM models.
- `backend/app/schemas/`: Pydantic schemas.
- `backend/app/routers/`: FastAPI route handlers.
- `frontend/src/views/`: Page components.
- `frontend/src/components/`: Reusable UI components.
- `frontend/src/stores/`: Pinia store definitions.

## Key Data Models
- **User Roles**: `admin`, `staff`, `cleaner`, `readonly`.
- **Room Status**: `available`, `occupied`, `cleaning`, `maintenance`.
- **APIKey**: Device-based authentication (tablet-in-room) for self-checkin.
- **CleaningRequest**: Guest-initiated requests tracked via `cleaning_requests` table.
