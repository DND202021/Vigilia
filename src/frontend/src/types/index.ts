/**
 * ERIOP Frontend Type Definitions
 */

// Authentication Types
export interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  role: UserRole;
  agency_id?: string;
  is_active: boolean;
  created_at: string;
  last_login?: string;
}

export type UserRole = 'admin' | 'dispatcher' | 'supervisor' | 'responder' | 'public';

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

// Role Types (for flexible RBAC)
export interface Role {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  hierarchy_level: number;
  color?: string;
  is_system_role: boolean;
  is_active: boolean;
  permissions: string[];
  user_count: number;
  created_at: string;
  updated_at: string;
}

export interface RoleCreateRequest {
  name: string;
  display_name: string;
  description?: string;
  hierarchy_level: number;
  color?: string;
  permissions: string[];
}

export interface RoleUpdateRequest {
  display_name?: string;
  description?: string;
  hierarchy_level?: number;
  color?: string;
  permissions?: string[];
  is_active?: boolean;
}

export interface Permission {
  key: string;
  name: string;
  description: string;
}

// User Management Types (full user for admin)
export interface UserFull {
  id: string;
  email: string;
  full_name: string;
  badge_number?: string;
  phone?: string;
  role_name: string;
  role_display_name: string;
  role?: {
    id: string;
    name: string;
    display_name: string;
    color?: string;
  };
  agency?: {
    id: string;
    name: string;
    code: string;
  };
  is_active: boolean;
  is_verified: boolean;
  mfa_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserCreateRequest {
  email: string;
  password: string;
  full_name: string;
  role_id?: string;
  agency_id?: string;
  badge_number?: string;
  phone?: string;
  is_verified?: boolean;
}

export interface UserUpdateRequest {
  full_name?: string;
  email?: string;
  role_id?: string;
  agency_id?: string;
  badge_number?: string;
  phone?: string;
  is_verified?: boolean;
}

export interface UserStats {
  total: number;
  active: number;
  inactive: number;
  verified: number;
  unverified: number;
  by_role: Record<string, number>;
}

export interface UserListResponse {
  items: UserFull[];
  total: number;
  page: number;
  page_size: number;
}

// Incident Types
export interface Incident {
  id: string;
  incident_number: string;
  incident_type: IncidentType;
  priority: IncidentPriority;
  status: IncidentStatus;
  title: string;
  description?: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  reported_at: string;
  dispatched_at?: string;
  on_scene_at?: string;
  resolved_at?: string;
  closed_at?: string;
  caller_name?: string;
  caller_phone?: string;
  agency_id: string;
  created_by_id?: string;
  assigned_units: string[];
  timeline_events: TimelineEvent[];
}

export type IncidentType = 'fire' | 'medical' | 'police' | 'traffic' | 'hazmat' | 'rescue' | 'other';
export type IncidentPriority = 1 | 2 | 3 | 4 | 5;
export type IncidentStatus = 'new' | 'assigned' | 'dispatched' | 'en_route' | 'on_scene' | 'resolved' | 'closed' | 'cancelled';

export interface TimelineEvent {
  timestamp: string;
  event_type: string;
  description: string;
  user_id?: string;
}

export interface IncidentCreateRequest {
  incident_type: IncidentType;
  priority: IncidentPriority;
  title: string;
  description?: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  caller_name?: string;
  caller_phone?: string;
}

export interface IncidentUpdateRequest {
  status?: IncidentStatus;
  priority?: IncidentPriority;
  description?: string;
  assigned_units?: string[];
}

// Resource Types
export interface Resource {
  id: string;
  resource_type: ResourceType;
  name: string;
  call_sign?: string;
  status: ResourceStatus;
  latitude?: number;
  longitude?: number;
  capabilities: string[];
  agency_id: string;
  current_incident_id?: string;
  last_status_update: string;
}

export type ResourceType = 'personnel' | 'vehicle' | 'equipment';
export type ResourceStatus = 'available' | 'dispatched' | 'en_route' | 'on_scene' | 'out_of_service' | 'off_duty';

export interface ResourceCreateRequest {
  resource_type: ResourceType;
  name: string;
  call_sign?: string;
  capabilities?: string[];
  agency_id?: string; // Required by backend, but frontend can get it from current user
}

export interface ResourceStatusUpdate {
  status: ResourceStatus;
  latitude?: number;
  longitude?: number;
}

// Alert Types
export interface Alert {
  id: string;
  alert_type: AlertType;
  severity: AlertSeverity;
  source: string;
  title: string;
  description?: string;
  latitude?: number;
  longitude?: number;
  status: AlertStatus;
  created_at: string;
  acknowledged_at?: string;
  acknowledged_by_id?: string;
  linked_incident_id?: string;
  raw_payload?: Record<string, unknown>;
}

export type AlertType = 'fire_alarm' | 'panic_alarm' | 'medical' | 'intrusion' | 'gunshot' | 'glass_break' | 'system' | 'other';
export type AlertSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type AlertStatus = 'new' | 'acknowledged' | 'investigating' | 'escalated' | 'resolved' | 'false_alarm';

export interface AlertAcknowledgeRequest {
  notes?: string;
}

export interface AlertCreateIncidentRequest {
  incident_type: IncidentType;
  priority: IncidentPriority;
  title?: string;
}

// Agency Types
export interface Agency {
  id: string;
  name: string;
  agency_type: AgencyType;
  jurisdiction?: string;
  is_active: boolean;
}

export type AgencyType = 'police' | 'fire' | 'ems' | 'dispatch' | 'other';

// API Response Types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiError {
  detail: string;
  status_code: number;
}

// Dashboard Stats
export interface DashboardStats {
  active_incidents: number;
  available_resources: number;
  pending_alerts: number;
  incidents_today: number;
  avg_response_time_minutes: number;
}

// Map Types
export interface MapMarker {
  id: string;
  type: 'incident' | 'resource' | 'alert';
  latitude: number;
  longitude: number;
  title: string;
  status: string;
  priority?: number;
  severity?: AlertSeverity;
}

// WebSocket Event Types
export interface WebSocketEvent {
  event_type: 'incident_created' | 'incident_updated' | 'alert_created' | 'resource_updated';
  payload: unknown;
  timestamp: string;
}

// Building Types
export interface Building {
  id: string;
  name: string;
  civic_number?: string;
  street_name: string;
  street_type?: string;
  unit_number?: string;
  city: string;
  province_state: string;
  postal_code?: string;
  country: string;
  full_address: string;
  latitude: number;
  longitude: number;
  building_type: BuildingType;
  occupancy_type?: OccupancyType;
  construction_type: ConstructionType;
  year_built?: number;
  year_renovated?: number;
  total_floors: number;
  basement_levels: number;
  total_area_sqm?: number;
  building_height_m?: number;
  max_occupancy?: number;
  hazard_level: HazardLevel;
  has_sprinkler_system: boolean;
  has_fire_alarm: boolean;
  has_standpipe: boolean;
  has_elevator: boolean;
  elevator_count?: number;
  has_generator: boolean;
  primary_entrance?: string;
  secondary_entrances?: string[];
  roof_access?: string;
  staging_area?: string;
  key_box_location?: string;
  knox_box: boolean;
  has_hazmat: boolean;
  hazmat_details?: HazmatDetail[];
  utilities_info?: Record<string, string>;
  owner_name?: string;
  owner_phone?: string;
  owner_email?: string;
  manager_name?: string;
  manager_phone?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  special_needs_occupants: boolean;
  special_needs_details?: string;
  animals_present: boolean;
  animals_details?: string;
  security_features?: string[];
  pre_incident_plan?: string;
  tactical_notes?: string;
  bim_file_url?: string;
  has_bim_data: boolean;
  external_id?: string;
  data_source?: string;
  is_verified: boolean;
  verified_at?: string;
  agency_id: string;
  created_at: string;
  updated_at: string;
}

export type BuildingType =
  | 'residential_single'
  | 'residential_multi'
  | 'commercial'
  | 'industrial'
  | 'institutional'
  | 'healthcare'
  | 'educational'
  | 'government'
  | 'religious'
  | 'mixed_use'
  | 'parking'
  | 'warehouse'
  | 'high_rise'
  | 'other';

export type OccupancyType =
  | 'assembly'
  | 'business'
  | 'educational'
  | 'factory'
  | 'high_hazard'
  | 'institutional'
  | 'mercantile'
  | 'residential'
  | 'storage'
  | 'utility';

export type ConstructionType =
  | 'type_i'
  | 'type_ii'
  | 'type_iii'
  | 'type_iv'
  | 'type_v'
  | 'unknown';

export type HazardLevel = 'low' | 'moderate' | 'high' | 'extreme';

export interface HazmatDetail {
  material: string;
  location: string;
  quantity?: string;
}

export interface FloorPlan {
  id: string;
  building_id: string;
  floor_number: number;
  floor_name?: string;
  plan_file_url?: string;
  plan_thumbnail_url?: string;
  file_type?: string;
  floor_area_sqm?: number;
  ceiling_height_m?: number;
  key_locations?: FloorKeyLocation[];
  emergency_exits?: FloorKeyLocation[];
  fire_equipment?: FloorKeyLocation[];
  hazards?: FloorKeyLocation[];
  notes?: string;
  has_bim_data: boolean;
  created_at: string;
  updated_at: string;
}

export interface FloorKeyLocation {
  type: string;
  name: string;
  x?: number;
  y?: number;
  description?: string;
}

export interface BuildingCreateRequest {
  name: string;
  civic_number?: string;
  street_name: string;
  street_type?: string;
  unit_number?: string;
  city: string;
  province_state: string;
  postal_code?: string;
  country?: string;
  latitude: number;
  longitude: number;
  building_type?: BuildingType;
  occupancy_type?: OccupancyType;
  construction_type?: ConstructionType;
  year_built?: number;
  total_floors?: number;
  basement_levels?: number;
  hazard_level?: HazardLevel;
  has_sprinkler_system?: boolean;
  has_fire_alarm?: boolean;
  has_elevator?: boolean;
  has_hazmat?: boolean;
  tactical_notes?: string;
}

export interface BuildingUpdateRequest {
  name?: string;
  building_type?: BuildingType;
  hazard_level?: HazardLevel;
  has_sprinkler_system?: boolean;
  has_fire_alarm?: boolean;
  has_standpipe?: boolean;
  has_elevator?: boolean;
  has_generator?: boolean;
  has_hazmat?: boolean;
  primary_entrance?: string;
  staging_area?: string;
  tactical_notes?: string;
}

export interface BuildingStats {
  total: number;
  verified: number;
  unverified: number;
  by_type: Record<string, number>;
  by_hazard_level: Record<string, number>;
  with_hazmat: number;
  with_sprinkler: number;
  high_rise: number;
}

// IoT Device Types
export type DeviceType = 'microphone' | 'camera' | 'sensor' | 'gateway' | 'other';
export type DeviceStatus = 'online' | 'offline' | 'alert' | 'maintenance' | 'error';

export interface IoTDevice {
  id: string;
  name: string;
  device_type: DeviceType;
  serial_number?: string;
  ip_address?: string;
  mac_address?: string;
  model?: string;
  firmware_version?: string;
  manufacturer?: string;
  building_id?: string;
  floor_plan_id?: string;
  position_x?: number;
  position_y?: number;
  latitude?: number;
  longitude?: number;
  location_name?: string;
  status: DeviceStatus;
  last_seen?: string;
  connection_quality?: number;
  config?: Record<string, unknown>;
  capabilities?: string[];
  metadata_extra?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface IoTDeviceCreateRequest {
  name: string;
  device_type: DeviceType;
  serial_number?: string;
  ip_address?: string;
  mac_address?: string;
  model?: string;
  firmware_version?: string;
  manufacturer?: string;
  building_id: string;
  floor_plan_id?: string;
  position_x?: number;
  position_y?: number;
  latitude?: number;
  longitude?: number;
  location_name?: string;
  config?: Record<string, unknown>;
  capabilities?: string[];
}

export interface IoTDeviceUpdateRequest {
  name?: string;
  device_type?: DeviceType;
  serial_number?: string;
  ip_address?: string;
  mac_address?: string;
  model?: string;
  firmware_version?: string;
  manufacturer?: string;
  building_id?: string;
  floor_plan_id?: string;
  location_name?: string;
  config?: Record<string, unknown>;
  capabilities?: string[];
}

export interface DevicePositionUpdate {
  position_x: number;
  position_y: number;
  floor_plan_id: string;
}

// Audio Clip Types
export interface AudioClip {
  id: string;
  alert_id?: string;
  device_id: string;
  file_path: string;
  file_size_bytes?: number;
  duration_seconds?: number;
  format?: string;
  sample_rate?: number;
  event_type: string;
  confidence?: number;
  peak_level_db?: number;
  background_level_db?: number;
  event_timestamp: string;
  captured_at: string;
  expires_at?: string;
}

// Sound Alert (extended Alert for sound anomaly context)
export interface SoundAlert extends Alert {
  device_id?: string;
  building_id?: string;
  floor_plan_id?: string;
  audio_clip_id?: string;
  confidence?: number;
  peak_level_db?: number;
  background_level_db?: number;
  risk_level?: string;
  occurrence_count?: number;
  last_occurrence?: string;
  assigned_to_id?: string;
}

// Notification Preference Types
export interface NotificationPreference {
  id: string;
  user_id: string;
  call_enabled: boolean;
  sms_enabled: boolean;
  email_enabled: boolean;
  push_enabled: boolean;
  building_ids: string[];
  min_severity: number;
  quiet_start?: string;
  quiet_end?: string;
  quiet_override_critical: boolean;
}

export interface NotificationPreferenceUpdate {
  call_enabled?: boolean;
  sms_enabled?: boolean;
  email_enabled?: boolean;
  push_enabled?: boolean;
  building_ids?: string[];
  min_severity?: number;
  quiet_start?: string;
  quiet_end?: string;
  quiet_override_critical?: boolean;
}

// Alert History Chart Data
export interface AlertHistoryPoint {
  date: string;
  severity: string;
  count: number;
}

// Building Alert Count
export interface BuildingAlertCount {
  building_id: string;
  active_alert_count: number;
}
