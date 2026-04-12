# 房務清潔通報功能設計

## Context

目前退房後房間狀態會變為 `cleaning`，但需要手動透過 PATCH API 將狀態改回 `available`。
此功能新增：
1. 外部裝置（清潔人員平板/感應器）呼叫 API 回報清潔完成
2. 前台人員在系統中手動標記清潔完成
3. 連住房客每日清潔流程支援
4. 完整的清潔紀錄追蹤
5. API Key 管理供外部裝置認證

---

## 房間狀態流程

```
【退房清潔】
occupied ──[check-out]──→ cleaning ──[清潔完成]──→ available

【每日清潔（連住房客）】
occupied ──[前台標註可清潔]──→ cleaning ──[清潔完成]──→ occupied
```

### 狀態轉換規則

- **check-out**：`occupied` → `cleaning`（現有邏輯不變），同時自動建立 CleaningRecord（`cleaning_type=checkout`，`started_at=now`）
- **前台標註可清潔**：`occupied` → `cleaning`，同時建立 CleaningRecord（`cleaning_type=daily`，`started_at=now`）
- **清潔完成**：`cleaning` → 自動判斷目標狀態
  - 若該房間有進行中的訂房（`status=checked_in`）→ `occupied`
  - 若無進行中的訂房 → `available`
- **報到檢查**：仍然只接受 `available` 狀態的房間（現有邏輯不變）

---

## 資料模型

### ApiKey

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID PK | 主鍵 |
| key_hash | String(255) | API Key 的 bcrypt hash |
| key_prefix | String(8) | Key 前 8 碼，用於識別顯示 |
| name | String(100) | 裝置名稱（如「3F 清潔平板」） |
| is_active | Boolean, default=True | 啟停用 |
| created_at | DateTime | 建立時間 |
| last_used_at | DateTime, nullable | 最後使用時間 |

- Key 生成時完整顯示一次，之後只顯示 prefix
- 與密碼一樣用 bcrypt hash 儲存

### CleaningRecord

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID PK | 主鍵 |
| room_id | UUID FK(rooms.id) | 關聯房間 |
| cleaning_type | Enum(`checkout`, `daily`) | 清潔類型 |
| started_at | DateTime | 開始清潔時間（房間進入 cleaning 的時間） |
| completed_at | DateTime, nullable | 清潔完成時間 |
| cleaned_by_name | String(50), nullable | 清潔人員姓名 |
| reported_via | Enum(`device`, `staff`) | 回報來源 |
| api_key_id | UUID FK(api_keys.id), nullable | 裝置回報時記錄 Key |
| staff_user_id | UUID FK(users.id), nullable | 前台操作時記錄人員 |
| notes | Text, nullable | 備註 |

---

## API 端點

### 房務清潔（`/api/housekeeping`）

#### `POST /rooms/{room_number}/mark-cleaning`
- **認證**：JWT (staff/admin)
- **說明**：前台標註 occupied 房間可清潔
- **邏輯**：
  1. 驗證房間存在且狀態為 `occupied`
  2. 房間狀態 → `cleaning`
  3. 清潔類型固定為 `daily`（前台手動標註代表房客仍在住；`checkout` 類型僅由 check-out 流程自動建立）
  4. 建立 CleaningRecord（`started_at=now`，`completed_at=null`）
- **回應**：更新後的房間資訊 + CleaningRecord

#### `POST /rooms/{room_number}/clean-complete`
- **認證**：API Key (`X-API-Key` header) 或 JWT (staff/admin)
- **請求 Body**：`{ "cleaned_by_name": "王小明" (optional), "notes": "..." (optional) }`
- **說明**：回報清潔完成
- **邏輯**：
  1. 驗證房間存在且狀態為 `cleaning`
  2. 查找該房間最近的未完成 CleaningRecord
  3. 更新 CleaningRecord：`completed_at=now`，填入 `cleaned_by_name`、`reported_via`、`api_key_id` 或 `staff_user_id`
  4. 判斷房間目標狀態：查詢是否有 `checked_in` 的訂房 → `occupied` / `available`
  5. 更新房間狀態
- **回應**：更新後的房間資訊 + CleaningRecord

#### `GET /cleaning-records`
- **認證**：JWT (staff/admin)
- **查詢參數**：`room_id`、`date_from`、`date_to`、`cleaning_type`
- **說明**：查詢清潔紀錄列表

#### `GET /rooms/cleaning-status`
- **認證**：API Key 或 JWT
- **說明**：查詢所有 `cleaning` 狀態的房間（供裝置取得待清潔清單）
- **回應**：房間列表（房號、樓層、房型、清潔類型）

### API Key 管理（`/api/api-keys`）

#### `POST /`
- **認證**：JWT (admin only)
- **請求**：`{ "name": "3F 清潔平板" }`
- **回應**：`{ "id": uuid, "key": "neo_xxxxxxxx...", "name": "...", "key_prefix": "neo_xxxx" }`
- **注意**：完整 Key 僅此一次回傳

#### `GET /`
- **認證**：JWT (admin only)
- **回應**：所有 Key 列表（id、name、key_prefix、is_active、created_at、last_used_at）

#### `PATCH /{key_id}`
- **認證**：JWT (admin only)
- **請求**：`{ "name": "...", "is_active": false }`

#### `DELETE /{key_id}`
- **認證**：JWT (admin only)

---

## 認證設計

### API Key 認證 Dependency

新增 `get_api_key` dependency：
- 從 `X-API-Key` header 取得 Key
- 遍歷 active 的 API Key，用 bcrypt 比對 hash
- 驗證通過後更新 `last_used_at`
- 回傳 ApiKey 物件

### 雙重認證端點

`clean-complete` 和 `cleaning-status` 支援 API Key 或 JWT：
- 新增 `get_device_or_user` dependency
- 優先檢查 `X-API-Key` header，若有則走 API Key 認證
- 若無則走 JWT 認證
- 回傳認證結果（ApiKey 或 User）

---

## Check-out 流程修改

現有的 `check_out` 端點（`backend/app/routers/checkins.py`）需修改：
- 退房將房間設為 `cleaning` 後，同時建立 CleaningRecord（`cleaning_type=checkout`，`started_at=now`）

---

## 前端頁面

### RoomsView 增強
- 房間卡片顯示清潔狀態，以顏色/圖示區分（available=綠, occupied=藍, cleaning=橘, maintenance=紅）
- `occupied` 房間新增「標註可清潔」按鈕
- `cleaning` 房間新增「標記清潔完成」按鈕
- 顯示目前的 CleaningRecord 資訊（清潔類型、開始時間）

### CleaningView（新頁面）
- 路由：`/cleaning`，需 auth
- 清潔紀錄列表，支援日期和房間篩選
- 顯示：房號、清潔類型、來源、開始/完成時間、耗時、清潔人員
- Sidebar 新增「清潔紀錄」選項

### ApiKeysView（新頁面）
- 路由：`/api-keys`，admin only
- 列出所有 API Key（prefix + 名稱 + 狀態 + 最後使用時間）
- 新增 Key 彈窗（顯示完整 Key，提醒僅顯示一次，提供複製按鈕）
- 啟停用切換 / 刪除確認

### 路由與導航更新
- Vue Router 新增 `/cleaning` 和 `/api-keys` 路由
- App.vue sidebar 新增對應選項
- `/api-keys` 僅 admin 角色可見

---

## 需修改的檔案

### 後端新增
- `backend/app/models/api_key.py` — ApiKey model
- `backend/app/models/cleaning.py` — CleaningRecord model
- `backend/app/schemas/api_key.py` — API Key schemas
- `backend/app/schemas/cleaning.py` — CleaningRecord schemas
- `backend/app/routers/housekeeping.py` — 房務清潔 API
- `backend/app/routers/api_keys.py` — API Key 管理 API

### 後端修改
- `backend/app/models/__init__.py` — 註冊新 model
- `backend/app/main.py` — 註冊新 router
- `backend/app/dependencies.py` — 新增 API Key 認證 dependency
- `backend/app/routers/checkins.py` — check-out 時建立 CleaningRecord
- `backend/app/config.py` — 新增 API Key 前綴設定（可選）

### 前端新增
- `frontend/src/views/CleaningView.vue` — 清潔紀錄頁面
- `frontend/src/views/ApiKeysView.vue` — API Key 管理頁面

### 前端修改
- `frontend/src/views/RoomsView.vue` — 新增清潔操作按鈕
- `frontend/src/router/index.ts` — 新增路由
- `frontend/src/App.vue` — sidebar 新增選項
- `frontend/src/types/index.ts` — 新增 TypeScript 型別
- `frontend/src/api/client.ts` — 新增 API 呼叫函數（可選，或直接在 view 中呼叫）

### 資料庫
- 新增 Alembic migration：建立 `api_keys` 和 `cleaning_records` 表

---

## 測試驗證

### 後端測試
- API Key CRUD 測試
- API Key 認證 dependency 測試
- mark-cleaning 端點測試（happy path + 非 occupied 房間拒絕）
- clean-complete 端點測試：
  - 裝置 API Key 認證
  - JWT 認證
  - 退房清潔 → available
  - 每日清潔 → occupied
  - 非 cleaning 房間拒絕
- check-out 自動建立 CleaningRecord 測試
- cleaning-records 查詢篩選測試

### 手動驗證
1. 建立 API Key，確認完整 Key 僅顯示一次
2. 退房流程：退房 → 房間變 cleaning → 裝置呼叫 API → 房間變 available
3. 每日清潔：前台標註可清潔 → 裝置呼叫 API → 房間回到 occupied
4. 前台手動清潔完成
5. 清潔紀錄頁面篩選查詢
6. API Key 停用後裝置呼叫被拒絕
