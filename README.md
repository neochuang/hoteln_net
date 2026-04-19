# Grand Hilai Check-in System

飯店入住管理系統，提供旅客管理、房間管理、訂房、報到/退房、早餐管理、房務清潔通報等功能。

## Tech Stack

| 層級 | 技術 |
|------|------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2 |
| Frontend | Vue 3 (Composition API + `<script setup>`), TypeScript, Vite, Pinia, Vue Router, Axios |
| Database | PostgreSQL 15 (asyncpg driver) |
| Auth | JWT (access + refresh token), bcrypt, HTTPBearer |
| Infra | Docker Compose (db / backend / frontend) |

## Quick Start (Docker Compose)

### 首次啟動

```bash
# 1. 複製環境變數
cp .env.example .env

# 2. 建構並啟動所有服務（db、backend、frontend）
docker compose up -d --build

# 3. 執行資料庫 migration（建立所有資料表）
docker compose exec backend alembic upgrade head

# 4. 匯入種子資料（預設帳號、房型、房間）
docker compose exec backend python -m app.seed
```

啟動後：
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API 文件 (Swagger): http://localhost:8000/docs

### 日常啟動 / 關閉

```bash
# 啟動（資料庫資料會保留）
docker compose up -d

# 查看服務狀態
docker compose ps

# 查看即時 log
docker compose logs -f

# 查看單一服務 log
docker compose logs -f backend

# 關閉所有服務（保留資料庫資料）
docker compose down
```

### 完全清除（重新開始）

```bash
# 關閉服務並刪除資料庫 volume（所有資料會消失）
docker compose down -v

# 如需同時清除建構的 image
docker compose down -v --rmi local
```

清除後如需重新啟動，請重新執行「首次啟動」的步驟。

### 重建單一服務

```bash
# 後端程式碼有變更時重建
docker compose up -d --build backend

# 前端程式碼有變更時重建
docker compose up -d --build frontend
```

> 開發模式下 backend 和 frontend 都掛載了本地目錄並啟用 hot reload，一般程式碼修改不需要重建。只有 `Dockerfile`、`pyproject.toml`、`package.json` 等依賴設定變更時才需要 `--build`。

---

## 本地開發（不用 Docker）

### 資料庫

需要一個 PostgreSQL 15 實例，預設連線資訊：

```
postgresql+asyncpg://neo:neo_password@localhost:5432/neo_hotel
```

也可以只用 Docker 跑資料庫：

```bash
docker compose up -d db
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 執行資料庫 migration
alembic upgrade head

# 匯入種子資料
python -m app.seed

# 啟動開發伺服器（自動 reload）
uvicorn app.main:app --reload
```

Backend 預設跑在 http://localhost:8000

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend 預設跑在 http://localhost:5173

## 預設帳號

種子資料會建立以下帳號：

| 角色 | 帳號 | 密碼 | 說明 |
|------|------|------|------|
| Admin | `admin` | `admin123` | 系統管理員，完整權限 |
| Staff | `staff` | `staff123` | 前台人員，日常操作權限 |
| Cleaner | `cleaner1` | `cleaner1` | 清潔人員，僅能存取房務清潔頁面 |

> 種子資料另會建立一組綁定首個房間（201）的裝置 API Key，並將完整 key 印到 stdout。此 key 僅供本機開發使用，請勿在共用環境執行 seed。

## 預設房型與房間

| 房型 | 容量 | 基本價格 | 房間 |
|------|------|---------|------|
| 單人房 | 1 | 1,500 | 201, 202, 203 |
| 雙人房 | 2 | 2,500 | 301, 302, 303 |
| 家庭房 | 4 | 4,000 | 401, 402 |
| 套房 | 2 | 5,000 | 501, 502 |

## 專案結構

```
neo/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, router registration
│   │   ├── config.py            # pydantic-settings (env-based config)
│   │   ├── database.py          # async engine, session, Base
│   │   ├── dependencies.py      # get_current_user, require_role, API Key auth
│   │   ├── seed.py              # DB seed script
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── routers/             # API route handlers
│   │   ├── services/            # Business logic (auth service)
│   │   └── utils/
│   ├── tests/                   # pytest-asyncio tests
│   ├── alembic/                 # DB migrations
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.vue              # Layout: sidebar + topbar + router-view
│   │   ├── main.ts              # App entry point
│   │   ├── api/client.ts        # Axios instance with JWT interceptor
│   │   ├── stores/auth.ts       # Pinia auth store
│   │   ├── router/index.ts      # Vue Router with auth guards
│   │   ├── types/index.ts       # TypeScript type definitions
│   │   └── views/               # Page components
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── docs/
```

## API 端點

所有端點前綴為 `/api`：

| 前綴 | 標籤 | 說明 |
|------|------|------|
| `/auth` | Auth | 登入、refresh token、取得當前使用者 |
| `/users` | Users | 使用者 CRUD (admin only) |
| `/guests` | Guests | 旅客 CRUD |
| `/rooms` | Rooms | 房間與房型管理 |
| `/reservations` | Reservations | 訂房 CRUD |
| `/` | Check-in/out | 報到與退房操作 |
| `/breakfast` | Breakfast | 早餐紀錄管理 |
| `/self-checkin` | Self Check-in | 旅客自助報到 (public, 無需認證) |
| `/housekeeping` | Housekeeping | 房務清潔通報、旅客清潔請求 (支援 API Key 與 cleaner 角色) |
| `/api-keys` | API Keys | 外部裝置 API Key 管理，可綁定房間 (admin only) |

完整 API 文件請參考 Swagger UI: http://localhost:8000/docs

## 前端頁面

| 路由 | 元件 | 存取權限 |
|------|------|---------|
| `/login` | LoginView | public |
| `/` | DashboardView | auth |
| `/guests` | GuestsView | auth |
| `/rooms` | RoomsView | auth |
| `/reservations` | ReservationsView | auth |
| `/checkin` | CheckInView | admin, staff |
| `/breakfast` | BreakfastView | admin, staff |
| `/housekeeping` | HousekeepingView | admin, staff, cleaner |
| `/users` | UsersView | admin only |
| `/api-keys` | ApiKeysView | admin only |
| `/self-checkin` | SelfCheckInView | public |

> `cleaner` 角色登入後會自動導向 `/housekeeping`，側邊欄只顯示房務頁面；`/cleaning` 會重導到 `/housekeeping`（舊路徑相容）。

## 認證系統

- JWT access token (30 分鐘) + refresh token (7 天)
- Frontend 使用 Axios interceptor 自動 refresh token
- 角色：`admin`（完整權限）、`staff`（日常操作）、`cleaner`（僅限房務清潔）、`readonly`（唯讀）
- 外部裝置透過 `X-API-Key` header 認證（API Key 由 admin 建立，可選擇綁定到特定房間）
- 綁定房間的 API Key 可代表該房間旅客送出清潔請求（`POST /api/housekeeping/cleaning-requests`）

## 房間狀態流程

```
available ──[check-in]──→ occupied ──[check-out]──→ cleaning ──[清潔完成]──→ available
                              │                                    ↑
                              └──[前台標註可清潔]──→ cleaning ──[清潔完成]──→ occupied
                                 (每日清潔)                        (連住房客回復)
```

- 退房後房間自動進入 `cleaning` 狀態，並建立清潔紀錄
- 連住房客外出時，前台可標註房間為「可清潔」
- 清潔完成可由外部裝置（API Key）或前台人員回報
- 系統自動判斷清潔完成後的目標狀態（有進行中訂房 → `occupied`，無 → `available`）

## 旅客自助報到

旅客可透過自助報到頁面完成入住，無需登入系統。

- **頁面網址**: http://localhost:5173/self-checkin
- **流程**: 輸入證件號碼 → 選擇訂房 → 系統自動分配房間並完成報到
- **回傳資訊**: 房號、樓層、房型、入住/退房日期、早餐資訊、WiFi 密碼

### Self Check-in API

供自助報到機或 Kiosk 裝置串接，無需認證。

**查詢訂房：**

```bash
curl -X POST http://localhost:8000/api/self-checkin/lookup \
  -H "Content-Type: application/json" \
  -d '{"id_number": "A123456789"}'
```

**確認報到：**

```bash
curl -X POST http://localhost:8000/api/self-checkin/confirm \
  -H "Content-Type: application/json" \
  -d '{"reservation_id": "<訂房 UUID>", "id_number": "A123456789"}'
```

## 房務清潔 API

供清潔人員平板或感應器等外部裝置呼叫，使用 API Key 認證。

### 取得 API Key

由 Admin 在前端 API Key 管理頁面（http://localhost:5173/api-keys）建立，或透過 API：

```bash
curl -X POST http://localhost:8000/api/api-keys \
  -H "Authorization: Bearer <admin_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "301 房客房裝置", "room_id": "<房間 UUID>"}'
```

- `room_id` 為選填：綁定房間後，該裝置才能代表房間旅客送出清潔請求
- 回傳的 `key` 欄位即為完整 API Key（僅顯示一次，格式如 `neo_xxxxxxxx...`）
- 可用 `PATCH /api/api-keys/{id}` 更新 `room_id`（或設為 `null` 解除綁定）

### 查詢待清潔房間

```bash
curl http://localhost:8000/api/housekeeping/rooms/cleaning-status \
  -H "X-API-Key: neo_xxxxxxxx..."
```

### 回報清潔完成

```bash
curl -X POST http://localhost:8000/api/housekeeping/rooms/301/clean-complete \
  -H "X-API-Key: neo_xxxxxxxx..." \
  -H "Content-Type: application/json" \
  -d '{"cleaned_by_name": "王小明", "notes": "已更換床單"}'
```

- `cleaned_by_name` 和 `notes` 皆為選填
- 系統自動判斷清潔後狀態：有進行中訂房 → `occupied`，無 → `available`

### 前台標註房間可清潔

前台人員將連住房客外出的房間標註為可清潔（需 JWT 認證，`admin` / `staff` / `cleaner` 皆可）：

```bash
curl -X POST http://localhost:8000/api/housekeeping/rooms/301/mark-cleaning \
  -H "Authorization: Bearer <access_token>"
```

若該房間已有 `pending` 清潔請求，此操作會在同一個 transaction 內將請求標為 `fulfilled` 並連結到剛建立的清潔紀錄。

## 旅客清潔請求 API

房間內的裝置（綁定房間的 API Key）可代表旅客送出「請來打掃」的請求。請求在清潔完成（mark-cleaning）時會自動標為已處理。

### 送出清潔請求（裝置端）

```bash
curl -X POST http://localhost:8000/api/housekeeping/cleaning-requests \
  -H "X-API-Key: neo_xxxxxxxx..." \
  -H "Content-Type: application/json" \
  -d '{"notes": "希望補充礦泉水"}'
```

- 需使用已綁定房間的裝置 API Key；該房間必須為 `occupied` 狀態
- 同一房間在同一時間只能有一筆 `pending` 請求（partial unique index）；重複呼叫會回傳既有的 pending 請求（idempotent）
- `notes` 為選填

### 查詢清潔請求（前台 / 清潔人員）

```bash
# 預設列出所有 pending 請求
curl "http://localhost:8000/api/housekeeping/cleaning-requests" \
  -H "Authorization: Bearer <access_token>"

# 可用 status 過濾：pending / fulfilled / cancelled / all
curl "http://localhost:8000/api/housekeeping/cleaning-requests?status=all&room_id=<UUID>" \
  -H "Authorization: Bearer <access_token>"
```

可由 `admin`、`staff`、`cleaner` 角色呼叫。

### 取消清潔請求（前台）

```bash
curl -X POST http://localhost:8000/api/housekeeping/cleaning-requests/<request_id>/cancel \
  -H "Authorization: Bearer <access_token>"
```

- 僅 `admin` / `staff` 可取消
- 非 `pending` 狀態會回 `409 Conflict`

## 環境變數

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL 連線字串 | `postgresql+asyncpg://neo:neo_password@localhost:5432/neo_hotel` |
| `JWT_SECRET` | JWT 簽署金鑰 | `change-me-to-a-random-secret-key` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token 過期時間（分鐘） | `30` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token 過期時間（天） | `7` |

## 測試

```bash
cd backend
source .venv/bin/activate
pytest -v
```

測試使用 SQLite in-memory 資料庫，不需要 PostgreSQL。
