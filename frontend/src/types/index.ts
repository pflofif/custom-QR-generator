// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  username: string;
  email: string;
  role: "admin" | "user";
  telegram_chat_id: string | null;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// ─── Event ────────────────────────────────────────────────────────────────────

export interface Event {
  id: string;
  name: string;
  description: string | null;
  owner_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  qr_count: number;
  total_scans: number;
}

export interface EventCreatePayload {
  name: string;
  description?: string;
}

export interface EventUpdatePayload {
  name?: string;
  description?: string;
  is_active?: boolean;
}

// ─── QR Code ──────────────────────────────────────────────────────────────────

export interface QRCustomStyle {
  colorized: boolean;
  contrast: number;
  brightness: number;
  version: number;
  level: "L" | "M" | "Q" | "H";
  has_background: boolean;
  background_key: string | null;
}

export interface QRCode {
  id: string;
  short_id: string;
  label: string;
  target_url: string;
  event_id: string;
  owner_id: string;
  is_active: boolean;
  proxy_url: string;
  created_at: string;
  updated_at: string;
  scan_count: number;
  custom_style: QRCustomStyle | null;
}

export interface QRCreatePayload {
  label: string;
  target_url: string;
}

export interface QRUpdatePayload {
  label?: string;
  target_url?: string;
  is_active?: boolean;
}

// ─── Analytics ────────────────────────────────────────────────────────────────

export interface QRBreakdownItem {
  qr_id: string;
  label: string;
  short_id: string;
  scan_count: number;
  is_active: boolean;
}

export interface TimeSeriesPoint {
  date: string;
  count: number;
}

export interface DeviceBreakdownItem {
  device_type: string;
  count: number;
}

export interface BrowserItem {
  browser: string;
  count: number;
}

export interface EventAnalytics {
  event_id: string;
  event_name: string;
  total_scans: number;
  qr_breakdown: QRBreakdownItem[];
  time_series: TimeSeriesPoint[];
  device_breakdown: DeviceBreakdownItem[];
  top_browsers: BrowserItem[];
}

export interface OverviewAnalytics {
  total_events: number;
  total_qr_codes: number;
  total_scans_30d: number;
  total_scans_all: number;
}
