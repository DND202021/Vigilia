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
