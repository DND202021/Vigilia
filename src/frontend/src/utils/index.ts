/**
 * ERIOP Utility Functions
 */

import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { format, formatDistanceToNow, parseISO } from 'date-fns';
import type {
  IncidentPriority,
  IncidentStatus,
  AlertSeverity,
  ResourceStatus,
  IncidentType,
  AlertType,
} from '../types';

// Tailwind class merge utility
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Date formatting
export function formatDate(dateString: string): string {
  try {
    return format(parseISO(dateString), 'MMM d, yyyy HH:mm');
  } catch {
    return dateString;
  }
}

export function formatRelativeTime(dateString: string): string {
  try {
    return formatDistanceToNow(parseISO(dateString), { addSuffix: true });
  } catch {
    return dateString;
  }
}

export function formatTime(dateString: string): string {
  try {
    return format(parseISO(dateString), 'HH:mm:ss');
  } catch {
    return dateString;
  }
}

// Priority helpers
export const priorityConfig: Record<
  IncidentPriority,
  { label: string; color: string; bgColor: string }
> = {
  1: { label: 'Critical', color: 'text-red-700', bgColor: 'bg-red-100' },
  2: { label: 'High', color: 'text-orange-700', bgColor: 'bg-orange-100' },
  3: { label: 'Medium', color: 'text-yellow-700', bgColor: 'bg-yellow-100' },
  4: { label: 'Low', color: 'text-blue-700', bgColor: 'bg-blue-100' },
  5: { label: 'Info', color: 'text-gray-700', bgColor: 'bg-gray-100' },
};

export function getPriorityLabel(priority: IncidentPriority): string {
  return priorityConfig[priority]?.label || `P${priority}`;
}

export function getPriorityColor(priority: IncidentPriority): string {
  return priorityConfig[priority]?.color || 'text-gray-700';
}

export function getPriorityBgColor(priority: IncidentPriority): string {
  return priorityConfig[priority]?.bgColor || 'bg-gray-100';
}

// Status helpers - matches backend IncidentStatus enum
export const statusConfig: Record<IncidentStatus, { label: string; color: string; bgColor: string }> =
  {
    new: { label: 'New', color: 'text-blue-700', bgColor: 'bg-blue-100' },
    assigned: { label: 'Assigned', color: 'text-purple-700', bgColor: 'bg-purple-100' },
    en_route: { label: 'En Route / Dispatched', color: 'text-cyan-700', bgColor: 'bg-cyan-100' },
    on_scene: { label: 'On Scene', color: 'text-green-700', bgColor: 'bg-green-100' },
    resolved: { label: 'Resolved', color: 'text-teal-700', bgColor: 'bg-teal-100' },
    closed: { label: 'Closed', color: 'text-gray-700', bgColor: 'bg-gray-100' },
  };

export function getStatusLabel(status: IncidentStatus): string {
  return statusConfig[status]?.label || status;
}

export function getStatusColor(status: IncidentStatus): string {
  return statusConfig[status]?.color || 'text-gray-700';
}

export function getStatusBgColor(status: IncidentStatus): string {
  return statusConfig[status]?.bgColor || 'bg-gray-100';
}

// Severity helpers
export const severityConfig: Record<AlertSeverity, { label: string; color: string; bgColor: string }> =
  {
    critical: { label: 'Critical', color: 'text-red-700', bgColor: 'bg-red-100' },
    high: { label: 'High', color: 'text-orange-700', bgColor: 'bg-orange-100' },
    medium: { label: 'Medium', color: 'text-yellow-700', bgColor: 'bg-yellow-100' },
    low: { label: 'Low', color: 'text-blue-700', bgColor: 'bg-blue-100' },
    info: { label: 'Info', color: 'text-gray-700', bgColor: 'bg-gray-100' },
  };

export function getSeverityLabel(severity: AlertSeverity): string {
  return severityConfig[severity]?.label || severity;
}

export function getSeverityColor(severity: AlertSeverity): string {
  return severityConfig[severity]?.color || 'text-gray-700';
}

export function getSeverityBgColor(severity: AlertSeverity): string {
  return severityConfig[severity]?.bgColor || 'bg-gray-100';
}

// Resource status helpers
export const resourceStatusConfig: Record<
  ResourceStatus,
  { label: string; color: string; bgColor: string }
> = {
  available: { label: 'Available', color: 'text-green-700', bgColor: 'bg-green-100' },
  dispatched: { label: 'Dispatched', color: 'text-blue-700', bgColor: 'bg-blue-100' },
  en_route: { label: 'En Route', color: 'text-cyan-700', bgColor: 'bg-cyan-100' },
  on_scene: { label: 'On Scene', color: 'text-purple-700', bgColor: 'bg-purple-100' },
  out_of_service: { label: 'Out of Service', color: 'text-orange-700', bgColor: 'bg-orange-100' },
  off_duty: { label: 'Off Duty', color: 'text-gray-700', bgColor: 'bg-gray-100' },
};

export function getResourceStatusLabel(status: ResourceStatus): string {
  return resourceStatusConfig[status]?.label || status;
}

export function getResourceStatusColor(status: ResourceStatus): string {
  return resourceStatusConfig[status]?.color || 'text-gray-700';
}

// Incident type helpers
export const incidentTypeConfig: Record<IncidentType, { label: string; icon: string }> = {
  fire: { label: 'Fire', icon: '🔥' },
  medical: { label: 'Medical', icon: '🏥' },
  police: { label: 'Police', icon: '🚔' },
  traffic: { label: 'Traffic', icon: '🚗' },
  hazmat: { label: 'HazMat', icon: '☢️' },
  rescue: { label: 'Rescue', icon: '🆘' },
  other: { label: 'Other', icon: '📋' },
};

export function getIncidentTypeLabel(type: IncidentType): string {
  return incidentTypeConfig[type]?.label || type;
}

// Alert type helpers
export const alertTypeConfig: Record<AlertType, { label: string; icon: string }> = {
  fire_alarm: { label: 'Fire Alarm', icon: '🔥' },
  panic_alarm: { label: 'Panic Alarm', icon: '🚨' },
  medical: { label: 'Medical', icon: '🏥' },
  intrusion: { label: 'Intrusion', icon: '🚪' },
  gunshot: { label: 'Gunshot', icon: '💥' },
  glass_break: { label: 'Glass Break', icon: '🪟' },
  system: { label: 'System', icon: '⚙️' },
  other: { label: 'Other', icon: '📋' },
};

export function getAlertTypeLabel(type: AlertType): string {
  return alertTypeConfig[type]?.label || type;
}

// Geolocation
export function formatCoordinates(lat: number, lon: number): string {
  const latDir = lat >= 0 ? 'N' : 'S';
  const lonDir = lon >= 0 ? 'E' : 'W';
  return `${Math.abs(lat).toFixed(6)}° ${latDir}, ${Math.abs(lon).toFixed(6)}° ${lonDir}`;
}

export function calculateDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371000; // Earth's radius in meters
  const phi1 = (lat1 * Math.PI) / 180;
  const phi2 = (lat2 * Math.PI) / 180;
  const deltaPhi = ((lat2 - lat1) * Math.PI) / 180;
  const deltaLambda = ((lon2 - lon1) * Math.PI) / 180;

  const a =
    Math.sin(deltaPhi / 2) ** 2 +
    Math.cos(phi1) * Math.cos(phi2) * Math.sin(deltaLambda / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c;
}

export function formatDistance(meters: number): string {
  if (meters < 1000) {
    return `${Math.round(meters)} m`;
  }
  return `${(meters / 1000).toFixed(1)} km`;
}

// Debounce utility
export function debounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

// Local storage helpers
export function getStoredValue<T>(key: string, defaultValue: T): T {
  try {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : defaultValue;
  } catch {
    return defaultValue;
  }
}

export function setStoredValue<T>(key: string, value: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Ignore storage errors
  }
}
