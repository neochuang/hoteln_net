export interface User {
  id: string
  username: string
  full_name: string
  role: 'admin' | 'staff' | 'readonly'
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
