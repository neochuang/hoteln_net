# Grand Hilai Check-in System

## Project Overview

飯店入住管理系統，提供旅客管理、房間管理、訂房、報到/退房、早餐管理等功能。

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2
- **Frontend**: Vue 3 (Composition API + `<script setup>`), TypeScript, Vite, Pinia, Vue Router, Axios
- **Database**: PostgreSQL 15 (asyncpg driver)
- **Auth**: JWT (access + refresh token), bcrypt, HTTPBearer
- **Infra**: Docker Compose (db / backend / frontend)

## Project Structure

```
neo/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, router registration
│   │   ├── config.py          # pydantic-settings (env-based config)
│   │   ├── database.py        # async engine, session, Base
│   │   ├── dependencies.py    # get_current_user, require_role
│   │   ├── seed.py            # DB seed script
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── routers/           # API route handlers
│   │   ├── services/          # Business logic (auth service)
│   │   └── utils/
│   ├── tests/                 # pytest-asyncio tests
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.vue            # Layout: sidebar + topbar + router-view
│   │   ├── main.ts            # App entry point
│   │   ├── api/client.ts      # Axios instance with JWT interceptor + auto-refresh
│   │   ├── stores/auth.ts     # Pinia auth store (login, logout, init)
│   │   ├── router/index.ts    # Vue Router with auth guards
│   │   ├── types/index.ts     # TypeScript type definitions
│   │   └── views/             # Page components
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docker-compose.yml
├── .env / .env.example
└── docs/
```

## Data Models

- **User** — 系統使用者 (admin / staff / readonly)
- **Guest** — 旅客 (姓名、證件、國籍、聯絡方式)
- **RoomType** — 房型 (名稱、容量、基本價格)
- **Room** — 房間 (房號、樓層、狀態: available/occupied/cleaning/maintenance)
- **Reservation** — 訂房 (關聯 Guest + RoomType + Room, 日期、人數、含早餐、總價、狀態)
- **CheckInRecord** — 入住紀錄 (關聯 Reservation + Room, 入住/退房時間及操作者)
- **BreakfastRecord** — 早餐紀錄 (關聯 Reservation + Guest, 日期、額外購買)

## API Routes

All endpoints are prefixed with `/api`:

| Prefix             | Tag              | Description  |
|--------------------|------------------|-------------|
| `/auth`            | Auth             | 登入、refresh token、取得當前使用者 |
| `/users`           | Users            | 使用者 CRUD (admin only) |
| `/guests`          | Guests           | 旅客 CRUD |
| `/rooms`           | Rooms            | 房間與房型管理 |
| `/reservations`    | Reservations     | 訂房 CRUD |
| `/`                | Check-in/out     | 報到與退房操作 |
| `/breakfast`       | Breakfast        | 早餐紀錄管理 |
| `/self-checkin`    | Self Check-in    | 旅客自助報到 (public) |

## Frontend Pages

| Route            | Component            | Access     |
|------------------|----------------------|------------|
| `/login`         | LoginView            | public     |
| `/`              | DashboardView        | auth       |
| `/guests`        | GuestsView           | auth       |
| `/rooms`         | RoomsView            | auth       |
| `/reservations`  | ReservationsView     | auth       |
| `/checkin`       | CheckInView          | auth       |
| `/breakfast`     | BreakfastView        | auth       |
| `/users`         | UsersView            | admin only |
| `/self-checkin`  | SelfCheckInView      | public     |

## Auth System

- JWT access token (30 min) + refresh token (7 days)
- Frontend 使用 Axios interceptor 自動 refresh token
- Role-based access: `admin`, `staff`, `readonly`
- Backend 透過 `get_current_user` 和 `require_role()` dependency 實現權限控制

## Development Commands

```bash
# Docker 啟動全部服務
docker compose up -d

# Backend 本地開發
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload

# Frontend 本地開發
cd frontend
npm install
npm run dev

# 執行測試
cd backend
pytest

# Frontend build
cd frontend
npm run build
```

## Environment Variables

參考 `.env.example`:
- `DATABASE_URL` — PostgreSQL 連線字串
- `JWT_SECRET` — JWT 簽署金鑰
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` — Access token 過期時間
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS` — Refresh token 過期時間

## Conventions

- Backend 使用 async/await 全非同步架構
- Models 使用 SQLAlchemy 2.0 Mapped Column 語法
- 所有 primary key 使用 UUID
- Frontend 使用 Vue 3 Composition API (`<script setup>`)
- 前端狀態管理使用 Pinia
- API client 統一透過 `src/api/client.ts` 發送請求
