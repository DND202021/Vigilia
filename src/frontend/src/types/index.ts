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
  mfa_enabled?: boolean;
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

// MFA Types
export interface MFASetupResponse {
  secret: string;
  qr_code: string;
  manual_entry_key: string;
}

export interface MFALoginResponse extends AuthTokens {
  mfa_required?: boolean;
  mfa_temp_token?: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
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
  building_id?: string;
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
  building_id?: string;
}

export interface IncidentUpdateRequest {
  title?: string;
  description?: string;
  incident_type?: IncidentType;
  priority?: IncidentPriority;
  status?: IncidentStatus;
  address?: string;
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
  contact_email?: string;
  contact_phone?: string;
  address?: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export type AgencyType = 'police' | 'fire' | 'ems' | 'dispatch' | 'other';

export interface AgencyUpdateRequest {
  name?: string;
  agency_type?: AgencyType;
  jurisdiction?: string;
  contact_email?: string;
  contact_phone?: string;
  address?: string;
}

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

// ============================================================================
// Location Marker Types
// ============================================================================

/**
 * Location marker type categories for floor plan annotations.
 * These represent various safety, access, utility, and hazard markers
 * that can be placed on floor plans for emergency response.
 */
export type LocationMarkerType =
  // Fire Equipment
  | 'fire_extinguisher'
  | 'fire_hose'
  | 'alarm_pull'
  | 'fire_alarm'        // Legacy alias for alarm_pull
  | 'sprinkler_control'
  // Access
  | 'stairwell'
  | 'elevator'
  | 'emergency_exit'
  | 'roof_access'
  // Utilities
  | 'electrical_panel'
  | 'gas_shutoff'
  | 'water_shutoff'
  // Hazards
  | 'hazmat'
  | 'hazard'            // Legacy generic hazard type
  | 'confined_space'
  | 'high_voltage'
  // Medical
  | 'aed'
  | 'first_aid'
  | 'eyewash'
  // Generic
  | 'custom';

/**
 * Category groupings for UI organization and filtering.
 * Each LocationMarkerType belongs to one of these categories.
 */
export type LocationMarkerCategory =
  | 'fire_equipment'
  | 'access'
  | 'utilities'
  | 'hazards'
  | 'medical';

/**
 * Individual marker on a floor plan.
 * Coordinates are optional for markers that haven't been placed yet.
 */
export interface FloorKeyLocation {
  id?: string;
  type: LocationMarkerType | string; // Allow string for backwards compatibility
  name: string;
  x?: number;  // percentage 0-100
  y?: number;  // percentage 0-100
  description?: string;
  notes?: string;
  createdAt?: string;
  updatedAt?: string;
}

/**
 * Floor key location with required coordinates.
 * Use this type for markers that have been placed on the floor plan.
 * This is the format expected by the API when saving markers.
 */
export interface FloorKeyLocationWithCoords extends Omit<FloorKeyLocation, 'x' | 'y'> {
  x: number;  // percentage 0-100 (required)
  y: number;  // percentage 0-100 (required)
}

/**
 * Marker type configuration for rendering.
 * Defines how each marker type should be displayed on floor plans.
 */
export interface MarkerTypeConfig {
  type: LocationMarkerType;
  category: LocationMarkerCategory;
  label: string;
  icon: string;   // emoji or icon name
  color: string;  // Tailwind color class or hex
}

/**
 * Mapping of marker types to their categories.
 * Used for filtering and grouping markers in the UI.
 */
export const MARKER_TYPE_CATEGORIES: Record<LocationMarkerType, LocationMarkerCategory> = {
  // Fire Equipment
  fire_extinguisher: 'fire_equipment',
  fire_hose: 'fire_equipment',
  alarm_pull: 'fire_equipment',
  fire_alarm: 'fire_equipment',
  sprinkler_control: 'fire_equipment',
  // Access
  stairwell: 'access',
  elevator: 'access',
  emergency_exit: 'access',
  roof_access: 'access',
  // Utilities
  electrical_panel: 'utilities',
  gas_shutoff: 'utilities',
  water_shutoff: 'utilities',
  // Hazards
  hazmat: 'hazards',
  hazard: 'hazards',
  confined_space: 'hazards',
  high_voltage: 'hazards',
  // Medical
  aed: 'medical',
  first_aid: 'medical',
  eyewash: 'medical',
  // Generic
  custom: 'access', // Default category for custom markers
};

/**
 * Default marker type configurations for rendering.
 * Provides icon, color, and label for each marker type.
 */
export const DEFAULT_MARKER_CONFIGS: MarkerTypeConfig[] = [
  // Fire Equipment
  { type: 'fire_extinguisher', category: 'fire_equipment', label: 'Fire Extinguisher', icon: '\u{1F9EF}', color: 'bg-red-500' },
  { type: 'fire_hose', category: 'fire_equipment', label: 'Fire Hose', icon: '\u{1F6BF}', color: 'bg-red-600' },
  { type: 'alarm_pull', category: 'fire_equipment', label: 'Alarm Pull Station', icon: '\u{1F514}', color: 'bg-red-400' },
  { type: 'fire_alarm', category: 'fire_equipment', label: 'Fire Alarm Pull', icon: '\u{1F514}', color: 'bg-red-400' },
  { type: 'sprinkler_control', category: 'fire_equipment', label: 'Sprinkler Control', icon: '\u{1F4A6}', color: 'bg-red-300' },
  // Access
  { type: 'stairwell', category: 'access', label: 'Stairwell', icon: '\u{1F6B6}', color: 'bg-blue-500' },
  { type: 'elevator', category: 'access', label: 'Elevator', icon: '\u{1F6D7}', color: 'bg-blue-400' },
  { type: 'emergency_exit', category: 'access', label: 'Emergency Exit', icon: '\u{1F6AA}', color: 'bg-green-500' },
  { type: 'roof_access', category: 'access', label: 'Roof Access', icon: '\u{1F3E0}', color: 'bg-blue-600' },
  // Utilities
  { type: 'electrical_panel', category: 'utilities', label: 'Electrical Panel', icon: '\u26A1', color: 'bg-yellow-500' },
  { type: 'gas_shutoff', category: 'utilities', label: 'Gas Shutoff', icon: '\u{1F525}', color: 'bg-orange-500' },
  { type: 'water_shutoff', category: 'utilities', label: 'Water Shutoff', icon: '\u{1F4A7}', color: 'bg-cyan-500' },
  // Hazards
  { type: 'hazmat', category: 'hazards', label: 'Hazmat', icon: '\u2622\uFE0F', color: 'bg-purple-500' },
  { type: 'hazard', category: 'hazards', label: 'Hazard', icon: '\u26A0\uFE0F', color: 'bg-amber-500' },
  { type: 'confined_space', category: 'hazards', label: 'Confined Space', icon: '\u{1F6AB}', color: 'bg-amber-600' },
  { type: 'high_voltage', category: 'hazards', label: 'High Voltage', icon: '\u26A1', color: 'bg-amber-400' },
  // Medical
  { type: 'aed', category: 'medical', label: 'AED', icon: '\u{1F493}', color: 'bg-pink-500' },
  { type: 'first_aid', category: 'medical', label: 'First Aid Kit', icon: '\u2695\uFE0F', color: 'bg-pink-400' },
  { type: 'eyewash', category: 'medical', label: 'Eyewash Station', icon: '\u{1F441}\uFE0F', color: 'bg-pink-300' },
  // Generic
  { type: 'custom', category: 'access', label: 'Location', icon: '\u{1F4CD}', color: 'bg-gray-500' },
];

/**
 * Helper to get marker config by type.
 */
export function getMarkerConfig(type: LocationMarkerType | string): MarkerTypeConfig | undefined {
  return DEFAULT_MARKER_CONFIGS.find(c => c.type === type);
}

/**
 * Helper to get all marker types for a category.
 */
export function getMarkerTypesByCategory(category: LocationMarkerCategory): LocationMarkerType[] {
  return (Object.entries(MARKER_TYPE_CATEGORIES) as [LocationMarkerType, LocationMarkerCategory][])
    .filter(([, cat]) => cat === category)
    .map(([type]) => type);
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
  // Basic info
  name?: string;
  civic_number?: string;
  street_name?: string;
  street_type?: string;
  unit_number?: string;
  city?: string;
  province_state?: string;
  postal_code?: string;
  country?: string;
  latitude?: number;
  longitude?: number;
  // Building characteristics
  building_type?: BuildingType;
  occupancy_type?: OccupancyType;
  construction_type?: ConstructionType;
  year_built?: number;
  year_renovated?: number;
  total_floors?: number;
  basement_levels?: number;
  total_area_sqm?: number;
  building_height_m?: number;
  max_occupancy?: number;
  // Safety
  hazard_level?: HazardLevel;
  has_sprinkler_system?: boolean;
  has_fire_alarm?: boolean;
  has_standpipe?: boolean;
  has_elevator?: boolean;
  elevator_count?: number;
  has_generator?: boolean;
  has_hazmat?: boolean;
  knox_box?: boolean;
  // Access
  primary_entrance?: string;
  staging_area?: string;
  key_box_location?: string;
  roof_access?: string;
  // Contacts
  owner_name?: string;
  owner_phone?: string;
  owner_email?: string;
  manager_name?: string;
  manager_phone?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  // Special info
  special_needs_occupants?: boolean;
  special_needs_details?: string;
  animals_present?: boolean;
  animals_details?: string;
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

// Device Icon Types for floor plan visualization
// Organized by category for first responders and tactical teams
export type DeviceIconType =
  // Surveillance & Audio
  | 'camera_dome'
  | 'camera_ptz'
  | 'camera_bullet'
  | 'camera_thermal'
  | 'camera_body'
  | 'microphone'
  | 'microphone_array'
  | 'speaker'
  // Motion & Presence
  | 'motion_sensor'
  | 'pir_sensor'
  | 'radar_sensor'
  | 'lidar_sensor'
  | 'occupancy_sensor'
  // Access Control
  | 'door_sensor'
  | 'window_sensor'
  | 'glass_break'
  | 'card_reader'
  | 'keypad'
  | 'biometric'
  // Environmental
  | 'smoke_detector'
  | 'heat_detector'
  | 'gas_detector'
  | 'co_detector'
  | 'water_leak'
  | 'temperature'
  | 'humidity'
  // Communication & Network
  | 'gateway'
  | 'repeater'
  | 'radio'
  | 'intercom'
  | 'panic_button'
  // Tactical
  | 'entry_point'
  | 'breach_point'
  | 'sniper_position'
  | 'observation_post'
  | 'rally_point'
  | 'hostage_location'
  | 'threat_location'
  // Generic
  | 'custom';

export type DeviceIconCategory =
  | 'surveillance'
  | 'motion'
  | 'access'
  | 'environmental'
  | 'communication'
  | 'tactical';

export interface DeviceIconConfig {
  type: DeviceIconType;
  category: DeviceIconCategory;
  label: string;
  icon: string;
  color: string;
  description?: string;
}

// Device icon configurations for floor plan display
export const DEFAULT_DEVICE_ICON_CONFIGS: DeviceIconConfig[] = [
  // Surveillance & Audio
  { type: 'camera_dome', category: 'surveillance', label: 'Dome Camera', icon: '🔵', color: 'bg-blue-500', description: 'Fixed dome surveillance camera' },
  { type: 'camera_ptz', category: 'surveillance', label: 'PTZ Camera', icon: '🎥', color: 'bg-blue-600', description: 'Pan-tilt-zoom camera' },
  { type: 'camera_bullet', category: 'surveillance', label: 'Bullet Camera', icon: '📹', color: 'bg-blue-500', description: 'Fixed bullet camera' },
  { type: 'camera_thermal', category: 'surveillance', label: 'Thermal Camera', icon: '🌡️', color: 'bg-orange-500', description: 'Thermal imaging camera' },
  { type: 'camera_body', category: 'surveillance', label: 'Body Camera', icon: '📷', color: 'bg-blue-400', description: 'Body-worn camera' },
  { type: 'microphone', category: 'surveillance', label: 'Microphone', icon: '🎙️', color: 'bg-purple-500', description: 'Audio monitoring microphone' },
  { type: 'microphone_array', category: 'surveillance', label: 'Mic Array', icon: '🎚️', color: 'bg-purple-600', description: 'Multi-directional microphone array' },
  { type: 'speaker', category: 'surveillance', label: 'Speaker', icon: '🔊', color: 'bg-purple-400', description: 'Audio announcement speaker' },

  // Motion & Presence
  { type: 'motion_sensor', category: 'motion', label: 'Motion Sensor', icon: '👁️', color: 'bg-cyan-500', description: 'Motion detection sensor' },
  { type: 'pir_sensor', category: 'motion', label: 'PIR Sensor', icon: '📡', color: 'bg-cyan-500', description: 'Passive infrared sensor' },
  { type: 'radar_sensor', category: 'motion', label: 'Radar Sensor', icon: '📶', color: 'bg-cyan-600', description: 'Radar-based motion detection' },
  { type: 'lidar_sensor', category: 'motion', label: 'LiDAR Sensor', icon: '🔦', color: 'bg-cyan-700', description: 'Laser-based 3D scanning' },
  { type: 'occupancy_sensor', category: 'motion', label: 'Occupancy', icon: '👥', color: 'bg-cyan-400', description: 'Room occupancy detection' },

  // Access Control
  { type: 'door_sensor', category: 'access', label: 'Door Sensor', icon: '🚪', color: 'bg-amber-500', description: 'Door open/close sensor' },
  { type: 'window_sensor', category: 'access', label: 'Window Sensor', icon: '🪟', color: 'bg-amber-400', description: 'Window open/close sensor' },
  { type: 'glass_break', category: 'access', label: 'Glass Break', icon: '💥', color: 'bg-amber-600', description: 'Glass break acoustic sensor' },
  { type: 'card_reader', category: 'access', label: 'Card Reader', icon: '💳', color: 'bg-amber-500', description: 'Access card reader' },
  { type: 'keypad', category: 'access', label: 'Keypad', icon: '🔢', color: 'bg-amber-500', description: 'PIN entry keypad' },
  { type: 'biometric', category: 'access', label: 'Biometric', icon: '👆', color: 'bg-amber-600', description: 'Fingerprint/face recognition' },

  // Environmental
  { type: 'smoke_detector', category: 'environmental', label: 'Smoke Detector', icon: '💨', color: 'bg-red-500', description: 'Smoke detection sensor' },
  { type: 'heat_detector', category: 'environmental', label: 'Heat Detector', icon: '🔥', color: 'bg-red-600', description: 'Heat/fire detection' },
  { type: 'gas_detector', category: 'environmental', label: 'Gas Detector', icon: '⚠️', color: 'bg-yellow-500', description: 'Gas leak detection' },
  { type: 'co_detector', category: 'environmental', label: 'CO Detector', icon: '☁️', color: 'bg-gray-500', description: 'Carbon monoxide detector' },
  { type: 'water_leak', category: 'environmental', label: 'Water Leak', icon: '💧', color: 'bg-blue-400', description: 'Water leak sensor' },
  { type: 'temperature', category: 'environmental', label: 'Temperature', icon: '🌡️', color: 'bg-green-500', description: 'Temperature sensor' },
  { type: 'humidity', category: 'environmental', label: 'Humidity', icon: '💦', color: 'bg-teal-500', description: 'Humidity sensor' },

  // Communication & Network
  { type: 'gateway', category: 'communication', label: 'Gateway', icon: '🔌', color: 'bg-gray-600', description: 'Network gateway/hub' },
  { type: 'repeater', category: 'communication', label: 'Repeater', icon: '📡', color: 'bg-gray-500', description: 'Signal repeater' },
  { type: 'radio', category: 'communication', label: 'Radio', icon: '📻', color: 'bg-indigo-500', description: 'Two-way radio base' },
  { type: 'intercom', category: 'communication', label: 'Intercom', icon: '🔔', color: 'bg-indigo-400', description: 'Intercom station' },
  { type: 'panic_button', category: 'communication', label: 'Panic Button', icon: '🆘', color: 'bg-red-600', description: 'Emergency panic button' },

  // Tactical (for SWAT/first responders)
  { type: 'entry_point', category: 'tactical', label: 'Entry Point', icon: '🚨', color: 'bg-green-600', description: 'Planned entry point' },
  { type: 'breach_point', category: 'tactical', label: 'Breach Point', icon: '💢', color: 'bg-orange-600', description: 'Tactical breach location' },
  { type: 'sniper_position', category: 'tactical', label: 'Sniper Position', icon: '🎯', color: 'bg-slate-700', description: 'Sniper/overwatch position' },
  { type: 'observation_post', category: 'tactical', label: 'Observation Post', icon: '👀', color: 'bg-slate-600', description: 'Surveillance observation point' },
  { type: 'rally_point', category: 'tactical', label: 'Rally Point', icon: '🏁', color: 'bg-green-500', description: 'Team rally/staging point' },
  { type: 'hostage_location', category: 'tactical', label: 'Hostage Location', icon: '🧑', color: 'bg-yellow-600', description: 'Known hostage position' },
  { type: 'threat_location', category: 'tactical', label: 'Threat Location', icon: '⚡', color: 'bg-red-700', description: 'Known threat position' },

  // Generic
  { type: 'custom', category: 'surveillance', label: 'Custom', icon: '📍', color: 'bg-gray-400', description: 'Custom device marker' },
];

// Device icon color options
export const DEVICE_ICON_COLORS = [
  { name: 'Red', value: 'bg-red-500', hex: '#ef4444' },
  { name: 'Orange', value: 'bg-orange-500', hex: '#f97316' },
  { name: 'Amber', value: 'bg-amber-500', hex: '#f59e0b' },
  { name: 'Yellow', value: 'bg-yellow-500', hex: '#eab308' },
  { name: 'Lime', value: 'bg-lime-500', hex: '#84cc16' },
  { name: 'Green', value: 'bg-green-500', hex: '#22c55e' },
  { name: 'Emerald', value: 'bg-emerald-500', hex: '#10b981' },
  { name: 'Teal', value: 'bg-teal-500', hex: '#14b8a6' },
  { name: 'Cyan', value: 'bg-cyan-500', hex: '#06b6d4' },
  { name: 'Sky', value: 'bg-sky-500', hex: '#0ea5e9' },
  { name: 'Blue', value: 'bg-blue-500', hex: '#3b82f6' },
  { name: 'Indigo', value: 'bg-indigo-500', hex: '#6366f1' },
  { name: 'Violet', value: 'bg-violet-500', hex: '#8b5cf6' },
  { name: 'Purple', value: 'bg-purple-500', hex: '#a855f7' },
  { name: 'Fuchsia', value: 'bg-fuchsia-500', hex: '#d946ef' },
  { name: 'Pink', value: 'bg-pink-500', hex: '#ec4899' },
  { name: 'Rose', value: 'bg-rose-500', hex: '#f43f5e' },
  { name: 'Slate', value: 'bg-slate-500', hex: '#64748b' },
  { name: 'Gray', value: 'bg-gray-500', hex: '#6b7280' },
];

// Helper functions for device icons
export function getDeviceIconConfig(type: DeviceIconType | string): DeviceIconConfig | undefined {
  return DEFAULT_DEVICE_ICON_CONFIGS.find((config) => config.type === type);
}

export function getDeviceIconsByCategory(category: DeviceIconCategory): DeviceIconConfig[] {
  return DEFAULT_DEVICE_ICON_CONFIGS.filter((config) => config.category === category);
}

export function getDefaultIconForDeviceType(deviceType: DeviceType): DeviceIconConfig {
  const mapping: Record<DeviceType, DeviceIconType> = {
    microphone: 'microphone',
    camera: 'camera_dome',
    sensor: 'motion_sensor',
    gateway: 'gateway',
    other: 'custom',
  };
  return getDeviceIconConfig(mapping[deviceType]) || DEFAULT_DEVICE_ICON_CONFIGS[DEFAULT_DEVICE_ICON_CONFIGS.length - 1];
}

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
  icon_type?: DeviceIconType | string;
  icon_color?: string;
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
  icon_type?: DeviceIconType | string;
  icon_color?: string;
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
  floor_plan_id?: string | null;
  position_x?: number | null;
  position_y?: number | null;
  location_name?: string;
  icon_type?: DeviceIconType | string | null;
  icon_color?: string | null;
  config?: Record<string, unknown>;
  capabilities?: string[];
}

export interface DevicePositionUpdate {
  position_x: number;
  position_y: number;
  floor_plan_id: string;
}

export interface DeviceStatusHistory {
  id: string;
  device_id: string;
  old_status: string | null;
  new_status: string;
  changed_at: string;
  reason: string | null;
  connection_quality: number | null;
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

// BIM Import types
export interface BIMFloorInfo {
  floor_number: number;
  floor_name: string;
  elevation?: number;
  area_sqm?: number;
  ceiling_height_m?: number;
  spaces?: BIMSpaceInfo[];
}

export interface BIMSpaceInfo {
  name: string;
  type: string; // room, corridor, stairwell, etc.
  area_sqm?: number;
  x?: number;
  y?: number;
}

export interface BIMKeyLocation {
  type: string; // door, stairwell, elevator, fire_extinguisher
  name: string;
  floor_number: number;
  x: number;
  y: number;
}

export interface BIMData {
  source_file?: string;
  import_date?: string;
  building_name?: string;
  construction_type?: string;
  construction_year?: number;
  total_area_sqm?: number;
  building_height_m?: number;
  floors: BIMFloorInfo[];
  key_locations?: BIMKeyLocation[];
  materials?: string[];
  raw_properties?: Record<string, any>;
}

export interface BIMImportResult {
  success: boolean;
  message?: string;
  bim_data?: BIMData;
  floors_created?: number;
  locations_found?: number;
}

// ============================================================================
// Document Management Types (Sprint 6)
// ============================================================================

export type DocumentCategory =
  | 'pre_plan'
  | 'floor_plan'
  | 'permit'
  | 'inspection'
  | 'manual'
  | 'other';

export interface BuildingDocument {
  id: string;
  building_id: string;
  category: DocumentCategory;
  title: string;
  description?: string;
  file_url: string;
  file_type: string;
  file_size: number;
  uploaded_by_id?: string;
  uploaded_by_name?: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentCreateRequest {
  title: string;
  description?: string;
  category: DocumentCategory;
}

export interface DocumentUpdateRequest {
  title?: string;
  description?: string;
  category?: DocumentCategory;
}

// ============================================================================
// Photo Management Types (Sprint 6)
// ============================================================================

export interface BuildingPhoto {
  id: string;
  building_id: string;
  floor_plan_id?: string;
  title: string;
  description?: string;
  file_url: string;
  thumbnail_url?: string;
  latitude?: number;
  longitude?: number;
  taken_at?: string;
  uploaded_by_id?: string;
  uploaded_by_name?: string;
  tags: string[];
  created_at: string;
}

export interface PhotoCreateRequest {
  title: string;
  description?: string;
  floor_plan_id?: string;
  latitude?: number;
  longitude?: number;
  taken_at?: string;
  tags?: string[];
}

// ============================================================================
// Inspection Tracking Types (Sprint 6)
// ============================================================================

export type InspectionType =
  | 'fire_safety'
  | 'structural'
  | 'hazmat'
  | 'general';

export type InspectionStatus =
  | 'scheduled'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'overdue';

export interface Inspection {
  id: string;
  building_id: string;
  inspection_type: InspectionType;
  scheduled_date: string;
  completed_date?: string;
  status: InspectionStatus;
  inspector_name: string;
  findings?: string;
  follow_up_required: boolean;
  follow_up_date?: string;
  created_by_id?: string;
  created_at: string;
  updated_at: string;
}

export interface InspectionCreateRequest {
  inspection_type: InspectionType;
  scheduled_date: string;
  inspector_name: string;
}

export interface InspectionUpdateRequest {
  scheduled_date?: string;
  completed_date?: string;
  status?: InspectionStatus;
  inspector_name?: string;
  findings?: string;
  follow_up_required?: boolean;
  follow_up_date?: string;
}

// ============================================================================
// Real-time Collaboration Types (Sprint 7)
// ============================================================================

/**
 * User presence on a floor plan for collaborative editing.
 */
export interface UserPresence {
  user_id: string;
  user_name: string;
  user_role?: string;
  is_editing: boolean;
  joined_at: string;
  last_heartbeat?: string;
}

/**
 * Marker with optimistic update metadata.
 */
export interface OptimisticMarker extends FloorKeyLocation {
  client_id: string;
  is_optimistic: boolean;
  timestamp: string;
}

/**
 * Conflict detected when multiple users edit the same marker.
 */
export interface MarkerConflict {
  marker_id: string;
  floor_plan_id: string;
  local_version: FloorKeyLocation;
  server_version: FloorKeyLocation;
  conflict_type: 'position' | 'properties' | 'deletion';
  detected_at: string;
  resolved?: boolean;
}

/**
 * Strategy for resolving marker conflicts.
 */
export type ConflictResolutionStrategy =
  | 'last_write_wins'
  | 'server_authoritative'
  | 'local_wins'
  | 'manual';

/**
 * Device position on a floor plan with real-time status.
 */
export interface DeviceFloorPosition {
  device_id: string;
  floor_plan_id: string;
  position_x: number;
  position_y: number;
  status: DeviceStatus;
  last_seen?: string;
  timestamp: string;
  // Device details for display
  device_name?: string;
  device_type?: DeviceType;
  icon_type?: DeviceIconType | string;
  icon_color?: string;
}

/**
 * WebSocket event data for marker operations.
 */
export interface MarkerWebSocketEvent {
  floor_plan_id: string;
  marker_id?: string;
  marker?: FloorKeyLocation;
  updates?: Partial<FloorKeyLocation>;
  user_id?: string;
  client_id?: string;
  timestamp: string;
}

/**
 * WebSocket event data for presence updates.
 */
export interface PresenceWebSocketEvent {
  floor_plan_id: string;
  user_id: string;
  user_name?: string;
  user_role?: string;
  is_editing?: boolean;
  timestamp: string;
}

/**
 * WebSocket event for presence list.
 */
export interface PresenceListEvent {
  floor_plan_id: string;
  active_users: UserPresence[];
  timestamp: string;
}

/**
 * WebSocket event for device position updates.
 */
export interface DevicePositionEvent {
  floor_plan_id: string;
  device_id: string;
  position_x: number;
  position_y: number;
  timestamp: string;
}

// ============================================================================
// Emergency Planning Types
// ============================================================================

export type EmergencyProcedureType =
  | 'evacuation'
  | 'fire'
  | 'medical'
  | 'hazmat'
  | 'lockdown'
  | 'active_shooter'
  | 'weather'
  | 'utility_failure';

export interface ProcedureStep {
  order: number;
  title: string;
  description: string;
  responsible_role?: string;
  duration_minutes?: number;
}

export interface ProcedureContact {
  name: string;
  role: string;
  phone?: string;
  email?: string;
}

export interface EmergencyProcedure {
  id: string;
  building_id: string;
  name: string;
  description?: string;
  procedure_type: EmergencyProcedureType;
  priority: number;
  steps: ProcedureStep[];
  contacts: ProcedureContact[];
  equipment_needed: string[];
  estimated_duration_minutes?: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type RouteType = 'primary' | 'secondary' | 'accessible' | 'emergency_vehicle';

export interface RouteWaypoint {
  order: number;
  x: number;
  y: number;
  floor_plan_id?: string;
  label?: string;
}

export interface EvacuationRoute {
  id: string;
  building_id: string;
  floor_plan_id?: string;
  name: string;
  description?: string;
  route_type: RouteType;
  waypoints: RouteWaypoint[];
  color: string;
  line_width: number;
  is_active: boolean;
  capacity?: number;
  estimated_time_seconds?: number;
  accessibility_features: string[];
  created_at: string;
  updated_at: string;
}

export type CheckpointType =
  | 'assembly_point'
  | 'muster_station'
  | 'first_aid'
  | 'command_post'
  | 'triage_area'
  | 'decontamination'
  | 'staging_area'
  | 'media_point';

export interface CheckpointEquipment {
  name: string;
  quantity: number;
  location?: string;
}

export interface CheckpointContactInfo {
  phone?: string;
  email?: string;
  radio_channel?: string;
}

export interface EmergencyCheckpoint {
  id: string;
  building_id: string;
  floor_plan_id?: string;
  name: string;
  checkpoint_type: CheckpointType;
  position_x: number;
  position_y: number;
  capacity?: number;
  equipment: CheckpointEquipment[];
  responsible_person?: string;
  contact_info?: CheckpointContactInfo;
  instructions?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// Emergency Plan Overview (combined response)
export interface EmergencyPlanOverview {
  building_id: string;
  procedures: EmergencyProcedure[];
  routes: EvacuationRoute[];
  checkpoints: EmergencyCheckpoint[];
}

// Audit Log Types
export type AuditAction =
  | 'login'
  | 'logout'
  | 'login_failed'
  | 'password_changed'
  | 'mfa_enabled'
  | 'mfa_disabled'
  | 'user_created'
  | 'user_updated'
  | 'user_deleted'
  | 'user_role_changed'
  | 'incident_created'
  | 'incident_updated'
  | 'incident_assigned'
  | 'incident_escalated'
  | 'incident_closed'
  | 'alert_received'
  | 'alert_acknowledged'
  | 'alert_dismissed'
  | 'alert_to_incident'
  | 'resource_created'
  | 'resource_updated'
  | 'resource_deleted'
  | 'resource_assigned'
  | 'resource_status_changed'
  | 'system_config_changed'
  | 'api_access'
  | 'permission_denied';

export interface AuditLog {
  id: string;
  timestamp: string;
  action: AuditAction;
  user_id: string | null;
  entity_type: string | null;
  entity_id: string | null;
  description: string | null;
  ip_address: string | null;
  old_values: Record<string, unknown> | null;
  new_values: Record<string, unknown> | null;
  metadata: Record<string, unknown> | null;
}

export interface AuditLogListResponse {
  items: AuditLog[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AuditLogFilters {
  action?: AuditAction;
  entity_type?: string;
  entity_id?: string;
  user_id?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  page_size?: number;
}

// === Telemetry Dashboard Types (Phase 23) ===

export interface TelemetryDataPoint {
  time: string;
  value: number | string | boolean | null;
}

export interface TelemetryAggregatePoint {
  time: string;
  metric_name: string;
  avg: number | null;
  min: number | null;
  max: number | null;
  count?: number | null;
}

export interface TelemetryQueryResponse {
  device_id: string;
  aggregation: string;
  count: number;
  data: TelemetryDataPoint[] | TelemetryAggregatePoint[];
}

export interface AvailableMetricsResponse {
  device_id: string;
  metrics: string[];
}

export interface TelemetryChartProps {
  deviceId: string;
  metricName: string;
  color?: string;
  height?: number;
}

export interface TelemetryEvent {
  device_id: string;
  metric_name: string;
  time: string;
  value: number | string | boolean | null;
}

export type DeviceSyncStatus = 'synced' | 'pending' | 'unknown';

export interface DeviceStatusInfo {
  status: DeviceStatus;
  lastSeen: string | null;
  isSynced: boolean;
}

export interface TimeRangePreset {
  label: string;
  value: () => [Date, Date];
}

// ============================================================================
// Device Provisioning Types (Phase 24)
// ============================================================================

export interface DeviceProvisionRequest {
  name: string;
  device_type: 'microphone' | 'camera' | 'sensor' | 'gateway';
  building_id: string;
  profile_id?: string;
  credential_type: 'access_token' | 'x509';
  serial_number?: string;
  manufacturer?: string;
  model?: string;
}

export interface DeviceProvisionResponse {
  device_id: string;
  name: string;
  device_type: string;
  building_id: string;
  provisioning_status: string;
  credential_type: string;
  access_token?: string;
  certificate_pem?: string;
  private_key_pem?: string;
  certificate_cn?: string;
  certificate_expiry?: string;
}

export interface DeviceStatusResponse {
  id: string;
  name: string;
  device_type: string;
  provisioning_status: string;
  status: string;
  last_seen: string | null;
}

export interface BulkProvisionResultItem {
  row: number;
  status: 'success' | 'error';
  device_id?: string;
  name?: string;
  credential_type?: string;
  error?: string;
}

export interface BulkProvisionResponse {
  total_rows: number;
  successful: number;
  failed: number;
  results: BulkProvisionResultItem[];
}

export interface DeviceProfile {
  id: string;
  name: string;
  device_type: string;
  description?: string;
  telemetry_keys?: string[];
  attributes?: Record<string, unknown>;
  alert_rules?: Record<string, unknown>;
}
