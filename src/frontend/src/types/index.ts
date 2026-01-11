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
