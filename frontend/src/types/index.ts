export interface User {
  id: string
  username: string
  full_name: string
  role: 'admin' | 'staff' | 'readonly' | 'cleaner'
  is_active: boolean
}

export interface Guest {
  id: string
  first_name: string
  last_name: string
  id_type: 'national_id' | 'passport' | 'other'
  id_number: string
  phone: string
  email: string | null
  nationality: string
  notes: string | null
  created_at: string
}

export interface RoomType {
  id: string
  name: string
  capacity: number
  base_price: number
  description: string | null
}

export interface Room {
  id: string
  room_number: string
  floor: number
  room_type_id: string
  status: 'available' | 'occupied' | 'cleaning' | 'maintenance'
  notes: string | null
  room_type?: RoomType
}

export interface Reservation {
  id: string
  guest_id: string
  room_type_id: string
  room_id: string | null
  check_in_date: string
  check_out_date: string
  num_guests: number
  status: 'confirmed' | 'checked_in' | 'checked_out' | 'cancelled'
  includes_breakfast: boolean
  breakfast_guests: number
  total_price: number
  notes: string | null
  created_by: string
  created_at: string
}

export interface BreakfastRecord {
  id: string
  reservation_id: string
  guest_id: string
  date: string
  meal_time: string
  is_extra_purchase: boolean
  extra_price: number | null
  recorded_by: string
}

export interface BreakfastStats {
  date: string
  total_meals: number
  included_meals: number
  extra_purchases: number
  extra_revenue: number
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface ApiKey {
  id: string
  key_prefix: string
  name: string
  is_active: boolean
  created_at: string
  last_used_at: string | null
  room_id: string | null
}

export interface ApiKeyCreated extends ApiKey {
  key: string
}

export interface CleaningRecord {
  id: string
  room_id: string
  cleaning_type: 'checkout' | 'daily'
  started_at: string
  completed_at: string | null
  cleaned_by_name: string | null
  reported_via: 'device' | 'staff' | null
  api_key_id: string | null
  staff_user_id: string | null
  notes: string | null
}

export interface MarkCleaningResponse {
  room_id: string
  room_number: string
  status: string
  cleaning_record: CleaningRecord
}

export interface CleanCompleteResponse {
  room_id: string
  room_number: string
  status: string
  cleaning_record: CleaningRecord | null
}

export interface CleaningStatusRoom {
  room_id: string
  room_number: string
  floor: number
  room_type_name: string
  cleaning_type: 'checkout' | 'daily'
  started_at: string
}

export interface CleaningRequest {
  id: string
  room_id: string
  room_number: string
  api_key_id: string
  notes: string | null
  status: 'pending' | 'fulfilled' | 'cancelled'
  requested_at: string
  fulfilled_at: string | null
  fulfilled_by_cleaning_record_id: string | null
  cancelled_at: string | null
  cancelled_by_user_id: string | null
}

export type CleaningTaskStatus = 'pending' | 'in_progress' | 'completed' | 'cancelled'

export interface CleaningTask {
  id: string
  room_id: string
  assigned_to_user_id: string
  assigned_by_user_id: string
  status: CleaningTaskStatus
  cleaning_type: string
  created_at: string
  updated_at: string
  room_number?: string
  cleaner_name?: string
}
