/**
 * Tactical Map Page
 */

import { useState, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useIncidentStore } from '../stores/incidentStore';
import { useResourceStore } from '../stores/resourceStore';
import { useAlertStore } from '../stores/alertStore';
import { usePolling } from '../hooks/useInterval';
import { Badge } from '../components/ui';
import {
  getPriorityLabel,
  getPriorityBgColor,
  getPriorityColor,
  getStatusLabel,
  getSeverityLabel,
  getSeverityBgColor,
  getResourceStatusLabel,
  formatRelativeTime,
  cn,
} from '../utils';
import type { Incident, Resource, Alert } from '../types';

const POLL_INTERVAL = 10000;
const DEFAULT_CENTER: [number, number] = [45.5017, -73.5673]; // Montreal
const DEFAULT_ZOOM = 12;

// Custom marker icons
const createIcon = (color: string, size: number = 24) => {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="${size}" height="${size}">
      <circle cx="12" cy="12" r="10" fill="${color}" stroke="white" stroke-width="2"/>
    </svg>
  `;
  return L.divIcon({
    html: svg,
    className: 'custom-marker',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
};

const incidentIcon = createIcon('#EF4444', 28); // Red
const resourceIcon = createIcon('#10B981', 24); // Green
const alertIcon = createIcon('#F59E0B', 26); // Yellow

// Priority-based incident icons
const incidentIcons: Record<number, L.DivIcon> = {
  1: createIcon('#DC2626', 32), // Critical - larger
  2: createIcon('#EF4444', 28), // High
  3: createIcon('#F97316', 26), // Medium
  4: createIcon('#3B82F6', 24), // Low
  5: createIcon('#6B7280', 22), // Info
};

export function MapPage() {
  const { activeIncidents, fetchActiveIncidents } = useIncidentStore();
  const { resources, fetchResources } = useResourceStore();
  const { pendingAlerts, fetchPendingAlerts } = useAlertStore();

  const [showIncidents, setShowIncidents] = useState(true);
  const [showResources, setShowResources] = useState(true);
  const [showAlerts, setShowAlerts] = useState(true);
  const [selectedItem, setSelectedItem] = useState<{
    type: 'incident' | 'resource' | 'alert';
    item: Incident | Resource | Alert;
  } | null>(null);

  // Fetch data
  usePolling(fetchActiveIncidents, POLL_INTERVAL);
  usePolling(() => fetchResources({}), POLL_INTERVAL);
  usePolling(fetchPendingAlerts, POLL_INTERVAL);

  // Filter items with coordinates
  const incidentsWithCoords = useMemo(
    () => activeIncidents.filter((i) => i.latitude && i.longitude),
    [activeIncidents]
  );

  const resourcesWithCoords = useMemo(
    () => resources.filter((r) => r.latitude && r.longitude),
    [resources]
  );

  const alertsWithCoords = useMemo(
    () => pendingAlerts.filter((a) => a.latitude && a.longitude),
    [pendingAlerts]
  );

  return (
    <div className="h-[calc(100vh-64px)] flex">
      {/* Sidebar */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        {/* Layer Controls */}
        <div className="p-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900 mb-3">Map Layers</h2>
          <div className="space-y-2">
            <LayerToggle
              label="Incidents"
              count={incidentsWithCoords.length}
              color="red"
              enabled={showIncidents}
              onChange={setShowIncidents}
            />
            <LayerToggle
              label="Resources"
              count={resourcesWithCoords.length}
              color="green"
              enabled={showResources}
              onChange={setShowResources}
            />
            <LayerToggle
              label="Alerts"
              count={alertsWithCoords.length}
              color="yellow"
              enabled={showAlerts}
              onChange={setShowAlerts}
            />
          </div>
        </div>

        {/* Selected Item Detail */}
        {selectedItem && (
          <div className="p-4 border-b border-gray-200 bg-gray-50">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs uppercase text-gray-500 font-medium">
                {selectedItem.type}
              </span>
              <button
                onClick={() => setSelectedItem(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <SelectedItemDetail item={selectedItem} />
          </div>
        )}

        {/* Items List */}
        <div className="flex-1 overflow-y-auto">
          {showIncidents && incidentsWithCoords.length > 0 && (
            <div className="p-4">
              <h3 className="text-sm font-medium text-gray-500 mb-2">
                Active Incidents ({incidentsWithCoords.length})
              </h3>
              <div className="space-y-2">
                {incidentsWithCoords.slice(0, 10).map((incident) => (
                  <ItemListCard
                    key={incident.id}
                    title={incident.incident_number}
                    subtitle={incident.title}
                    badge={
                      <Badge
                        size="sm"
                        className={cn(
                          getPriorityBgColor(incident.priority),
                          getPriorityColor(incident.priority)
                        )}
                      >
                        P{incident.priority}
                      </Badge>
                    }
                    onClick={() => setSelectedItem({ type: 'incident', item: incident })}
                    isSelected={selectedItem?.item === incident}
                  />
                ))}
              </div>
            </div>
          )}

          {showAlerts && alertsWithCoords.length > 0 && (
            <div className="p-4">
              <h3 className="text-sm font-medium text-gray-500 mb-2">
                Pending Alerts ({alertsWithCoords.length})
              </h3>
              <div className="space-y-2">
                {alertsWithCoords.slice(0, 10).map((alert) => (
                  <ItemListCard
                    key={alert.id}
                    title={alert.title}
                    subtitle={alert.source}
                    badge={
                      <Badge size="sm" className={getSeverityBgColor(alert.severity)}>
                        {getSeverityLabel(alert.severity)}
                      </Badge>
                    }
                    onClick={() => setSelectedItem({ type: 'alert', item: alert })}
                    isSelected={selectedItem?.item === alert}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Map */}
      <div className="flex-1 relative">
        <MapContainer
          center={DEFAULT_CENTER}
          zoom={DEFAULT_ZOOM}
          className="h-full w-full"
          zoomControl={false}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {/* Incidents */}
          {showIncidents &&
            incidentsWithCoords.map((incident) => (
              <Marker
                key={`incident-${incident.id}`}
                position={[incident.latitude!, incident.longitude!]}
                icon={incidentIcons[incident.priority] || incidentIcon}
                eventHandlers={{
                  click: () => setSelectedItem({ type: 'incident', item: incident }),
                }}
              >
                <Popup>
                  <div className="min-w-48">
                    <p className="font-semibold">{incident.incident_number}</p>
                    <p className="text-sm text-gray-600">{incident.title}</p>
                    <div className="mt-2 flex gap-2">
                      <Badge
                        size="sm"
                        className={cn(
                          getPriorityBgColor(incident.priority),
                          getPriorityColor(incident.priority)
                        )}
                      >
                        {getPriorityLabel(incident.priority)}
                      </Badge>
                      <Badge size="sm" variant="secondary">
                        {getStatusLabel(incident.status)}
                      </Badge>
                    </div>
                  </div>
                </Popup>
              </Marker>
            ))}

          {/* Resources */}
          {showResources &&
            resourcesWithCoords.map((resource) => (
              <Marker
                key={`resource-${resource.id}`}
                position={[resource.latitude!, resource.longitude!]}
                icon={resourceIcon}
                eventHandlers={{
                  click: () => setSelectedItem({ type: 'resource', item: resource }),
                }}
              >
                <Popup>
                  <div className="min-w-48">
                    <p className="font-semibold">{resource.call_sign || resource.name}</p>
                    <p className="text-sm text-gray-600 capitalize">{resource.resource_type}</p>
                    <div className="mt-2">
                      <Badge size="sm" variant="secondary">
                        {getResourceStatusLabel(resource.status)}
                      </Badge>
                    </div>
                  </div>
                </Popup>
              </Marker>
            ))}

          {/* Alerts */}
          {showAlerts &&
            alertsWithCoords.map((alert) => (
              <Marker
                key={`alert-${alert.id}`}
                position={[alert.latitude!, alert.longitude!]}
                icon={alertIcon}
                eventHandlers={{
                  click: () => setSelectedItem({ type: 'alert', item: alert }),
                }}
              >
                <Popup>
                  <div className="min-w-48">
                    <p className="font-semibold">{alert.title}</p>
                    <p className="text-sm text-gray-600">{alert.source}</p>
                    <div className="mt-2">
                      <Badge size="sm" className={getSeverityBgColor(alert.severity)}>
                        {getSeverityLabel(alert.severity)}
                      </Badge>
                    </div>
                  </div>
                </Popup>
              </Marker>
            ))}

          <MapControls />
        </MapContainer>

        {/* Legend */}
        <div className="absolute bottom-4 right-4 bg-white rounded-lg shadow-lg p-3 z-[1000]">
          <h4 className="text-xs font-medium text-gray-500 mb-2">Legend</h4>
          <div className="space-y-1 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <span>Incident</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span>Resource</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-yellow-500" />
              <span>Alert</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MapControls() {
  const map = useMap();

  return (
    <div className="absolute top-4 right-4 z-[1000] flex flex-col gap-2">
      <button
        onClick={() => map.zoomIn()}
        className="w-8 h-8 bg-white rounded shadow flex items-center justify-center hover:bg-gray-50"
      >
        +
      </button>
      <button
        onClick={() => map.zoomOut()}
        className="w-8 h-8 bg-white rounded shadow flex items-center justify-center hover:bg-gray-50"
      >
        -
      </button>
      <button
        onClick={() => map.setView(DEFAULT_CENTER, DEFAULT_ZOOM)}
        className="w-8 h-8 bg-white rounded shadow flex items-center justify-center hover:bg-gray-50 text-xs"
        title="Reset view"
      >
        R
      </button>
    </div>
  );
}

interface LayerToggleProps {
  label: string;
  count: number;
  color: 'red' | 'green' | 'yellow';
  enabled: boolean;
  onChange: (enabled: boolean) => void;
}

function LayerToggle({ label, count, color, enabled, onChange }: LayerToggleProps) {
  const colorStyles = {
    red: 'bg-red-500',
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
  };

  return (
    <label className="flex items-center gap-3 cursor-pointer">
      <input
        type="checkbox"
        checked={enabled}
        onChange={(e) => onChange(e.target.checked)}
        className="sr-only"
      />
      <div
        className={cn(
          'w-5 h-5 rounded border-2 flex items-center justify-center transition-colors',
          enabled ? 'bg-blue-600 border-blue-600' : 'border-gray-300'
        )}
      >
        {enabled && (
          <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
              clipRule="evenodd"
            />
          </svg>
        )}
      </div>
      <div className={cn('w-3 h-3 rounded-full', colorStyles[color])} />
      <span className="flex-1 text-sm">{label}</span>
      <span className="text-xs text-gray-500">{count}</span>
    </label>
  );
}

interface ItemListCardProps {
  title: string;
  subtitle: string;
  badge: React.ReactNode;
  onClick: () => void;
  isSelected: boolean;
}

function ItemListCard({
  title,
  subtitle,
  badge,
  onClick,
  isSelected,
}: ItemListCardProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left p-2 rounded-lg border transition-colors',
        isSelected
          ? 'border-blue-500 bg-blue-50'
          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
      )}
    >
      <div className="flex items-center justify-between">
        <span className="font-medium text-sm truncate">{title}</span>
        {badge}
      </div>
      <p className="text-xs text-gray-500 truncate mt-1">{subtitle}</p>
    </button>
  );
}

interface SelectedItemDetailProps {
  item: {
    type: 'incident' | 'resource' | 'alert';
    item: Incident | Resource | Alert;
  };
}

function SelectedItemDetail({ item }: SelectedItemDetailProps) {
  if (item.type === 'incident') {
    const incident = item.item as Incident;
    return (
      <div>
        <h3 className="font-semibold">{incident.incident_number}</h3>
        <p className="text-sm text-gray-600 mt-1">{incident.title}</p>
        <div className="mt-2 flex gap-2">
          <Badge
            size="sm"
            className={cn(
              getPriorityBgColor(incident.priority),
              getPriorityColor(incident.priority)
            )}
          >
            {getPriorityLabel(incident.priority)}
          </Badge>
          <Badge size="sm" variant="secondary">
            {getStatusLabel(incident.status)}
          </Badge>
        </div>
        {incident.address && (
          <p className="text-xs text-gray-500 mt-2">{incident.address}</p>
        )}
        <p className="text-xs text-gray-400 mt-1">
          {formatRelativeTime(incident.reported_at)}
        </p>
      </div>
    );
  }

  if (item.type === 'resource') {
    const resource = item.item as Resource;
    return (
      <div>
        <h3 className="font-semibold">{resource.call_sign || resource.name}</h3>
        <p className="text-sm text-gray-600 mt-1 capitalize">{resource.resource_type}</p>
        <Badge size="sm" variant="secondary" className="mt-2">
          {getResourceStatusLabel(resource.status)}
        </Badge>
        <p className="text-xs text-gray-400 mt-2">
          Updated {formatRelativeTime(resource.last_status_update)}
        </p>
      </div>
    );
  }

  if (item.type === 'alert') {
    const alert = item.item as Alert;
    return (
      <div>
        <h3 className="font-semibold">{alert.title}</h3>
        <p className="text-sm text-gray-600 mt-1">{alert.source}</p>
        <Badge size="sm" className={cn(getSeverityBgColor(alert.severity), 'mt-2')}>
          {getSeverityLabel(alert.severity)}
        </Badge>
        <p className="text-xs text-gray-400 mt-2">
          {formatRelativeTime(alert.created_at)}
        </p>
      </div>
    );
  }

  return null;
}
