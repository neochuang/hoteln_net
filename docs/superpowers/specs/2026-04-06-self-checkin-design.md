# Self-Service Check-in — Design Spec

## Overview

新增旅客自助報到功能。旅客可在大廳平板或自己的手機上，輸入證件號碼查詢訂房，確認身份後自動完成報到並取得房間資訊。不需登入員工帳號。

## Backend API

### POST `/api/self-checkin/lookup` (公開，不需認證)

查詢旅客的待報到訂房。

**Request:**
```json
{ "id_number": "A123456789" }
```

**Logic:**
1. 以 `id_number` 查詢 `guests` 表
2. 找到該旅客所有 `status = confirmed` 的訂房
3. Join `room_types` 取得房型名稱

**Response (200):**
```json
{
  "guest_name": "王大明",
  "reservations": [
    {
      "id": "uuid",
      "check_in_date": "2026-04-06",
      "check_out_date": "2026-04-08",
      "room_type_name": "雙人房",
      "num_guests": 2,
      "includes_breakfast": true,
      "breakfast_guests": 2
    }
  ]
}
```

**Error (404):** 找不到旅客或無待報到訂房。

### POST `/api/self-checkin/confirm` (公開，不需認證)

確認身份並完成自助報到。

**Request:**
```json
{
  "reservation_id": "uuid",
  "id_number": "A123456789"
}
```

**Logic:**
1. 驗證 reservation 存在且 status = confirmed
2. 驗證 reservation 對應的 guest 的 id_number 與輸入匹配
3. 從同房型的空房（status = available）中自動分配一間（取第一間）
4. 若無空房，回傳 400 錯誤
5. 更新 reservation: status → checked_in, room_id → 分配的房間
6. 更新 room: status → occupied
7. 建立 CheckInRecord: checked_in_by = NULL（表示自助報到）

**Response (200):**
```json
{
  "room_number": "301",
  "floor": 3,
  "room_type_name": "雙人房",
  "check_in_date": "2026-04-06",
  "check_out_date": "2026-04-08",
  "includes_breakfast": true,
  "breakfast_info": "早餐時間 07:00-10:00，地點：1F 餐廳",
  "wifi_password": "NeoHotel2026"
}
```

**Errors:**
- 404: 訂房不存在
- 400: 訂房非 confirmed 狀態 / 證件號碼不匹配 / 無可用空房

## Model Change

`CheckInRecord.checked_in_by`: 已經是 nullable，不需修改。

## Hotel Info Config

在 `app/config.py` 新增常數（不建 DB table，保持簡單）：

```python
wifi_password: str = "NeoHotel2026"
breakfast_info: str = "早餐時間 07:00-10:00，地點：1F 餐廳"
```

## Frontend

### 路由: `/self-checkin` (public)

獨立公開頁面，不在側邊欄顯示，不需登入。

### 頁面檔案: `frontend/src/views/SelfCheckInView.vue`

三步驟流程：

**Step 1 — 查詢**
- 大標題：「旅客自助報到」
- 輸入框：證件號碼
- 按鈕：查詢

**Step 2 — 確認**
- 顯示旅客姓名
- 列出匹配的訂房（日期、房型、人數、早餐）
- 每筆訂房有「確認報到」按鈕

**Step 3 — 完成**
- 大字顯示：房間號碼（醒目）
- 資訊卡片：樓層、退房日期、早餐資訊、WiFi 密碼
- 「完成」按鈕回到 Step 1（供下位旅客使用）

### 設計風格
- 大字體，適合平板觸控
- 簡潔白底，綠色成功主題
- 不顯示側邊欄和頂部工具列

## Backend Files to Create/Modify

- **New:** `backend/app/routers/self_checkin.py` — 公開 API
- **New:** `backend/app/schemas/self_checkin.py` — Request/Response schemas
- **Modify:** `backend/app/main.py` — 註冊新 router
- **Modify:** `backend/app/config.py` — 新增 wifi_password, breakfast_info

## Frontend Files to Create/Modify

- **New:** `frontend/src/views/SelfCheckInView.vue` — 自助報到頁面
- **Modify:** `frontend/src/router/index.ts` — 新增公開路由
- **Modify:** `frontend/src/App.vue` — 自助頁面不顯示側邊欄

## Testing

- **New:** `backend/tests/test_self_checkin.py`
  - lookup 成功：有 confirmed 訂房
  - lookup 失敗：無此旅客 / 無待報到訂房
  - confirm 成功：分配房間、狀態更新
  - confirm 失敗：證件不匹配 / 無空房 / 非 confirmed 狀態

## Verification

1. 開啟 `/self-checkin`，不需登入即可存取
2. 輸入 seed 旅客的證件號碼 → 顯示訂房列表
3. 點擊確認報到 → 顯示房間號碼和入住資訊
4. 後台確認：訂房狀態變為 checked_in、房間狀態變為 occupied
5. 再次查詢同證件號碼 → 該訂房不再出現（已報到）
6. pytest 所有測試通過
