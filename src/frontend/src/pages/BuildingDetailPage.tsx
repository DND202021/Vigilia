/**
 * BuildingDetailPage
 *
 * Full-page building detail view at /buildings/:id featuring:
 * - Two-column layout (sidebar + main content)
 * - Building info panel in sidebar
 * - Device monitoring panel in sidebar
 * - Floor selector strip
 * - FloorPlanEditor with marker editing capabilities (edit mode, drag-to-move, save)
 * - Sub-tabs for Alerts, Incidents, and Floor Plan Upload
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useBuildingDetailStore } from '../stores/buildingDetailStore';
import { FloorSelector } from '../components/buildings/FloorSelector';
import { BuildingInfoPanel } from '../components/buildings/BuildingInfoPanel';
import { FloorPlanEditor } from '../components/buildings/FloorPlanEditor';
import { FloorPlanUpload } from '../components/buildings';
import { DeviceMonitoringPanel } from '../components/devices/DeviceMonitoringPanel';
import { AlertsFloorTable } from '../components/alerts/AlertsFloorTable';
import { Badge, Button, Spinner } from '../components/ui';
import {
  cn,
  formatDate,
  getIncidentTypeLabel,
  getStatusLabel,
  getStatusBgColor,
  getStatusColor,
} from '../utils';
import { buildingsApi } from '../services/api';
import type { FloorKeyLocation, HazardLevel, Incident, PaginatedResponse } from '../types';

const buildingTypeLabels: Record<string, string> = {
  residential_single: 'Residential (Single)',
  residential_multi: 'Residential (Multi)',
  commercial: 'Commercial',
  industrial: 'Industrial',
  institutional: 'Institutional',
  healthcare: 'Healthcare',
  educational: 'Educational',
  government: 'Government',
  religious: 'Religious',
  mixed_use: 'Mixed Use',
  parking: 'Parking',
  warehouse: 'Warehouse',
  high_rise: 'High Rise',
  other: 'Other',
};

const hazardLevelConfig: Record<HazardLevel, { color: string; bgColor: string }> = {
  low: { color: 'text-green-700', bgColor: 'bg-green-100' },
  moderate: { color: 'text-yellow-700', bgColor: 'bg-yellow-100' },
  high: { color: 'text-orange-700', bgColor: 'bg-orange-100' },
  extreme: { color: 'text-red-700', bgColor: 'bg-red-100' },
};

type SubTab = 'alerts' | 'incidents' | 'upload';

export function BuildingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const {
    building,
    floorPlans,
    selectedFloor,
    devices,
    alerts,
    alertCount,
    selectedDevice,
    isPlacementMode,
    placementDeviceId,
    isLoading,
    isLoadingAlerts,
    error,
    fetchBuilding,
    fetchFloorPlans,
    fetchBuildingAlerts,
    selectFloor,
    setSelectedDevice,
    enterPlacementMode,
    exitPlacementMode,
    addFloorPlan,
    reset,
    clearError,
  } = useBuildingDetailStore();

  const [subTab, setSubTab] = useState<SubTab>('alerts');

  // Incident history state
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [incidentsLoading, setIncidentsLoading] = useState(false);
  const [incidentsError, setIncidentsError] = useState<string | null>(null);
  const [incidentsPagination, setIncidentsPagination] = useState<{
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
  }>({ page: 1, pageSize: 10, total: 0, totalPages: 0 });

  // Fetch incidents for the building
  const fetchIncidents = useCallback(
    async (page = 1, pageSize = 10) => {
      if (!id) return;
      setIncidentsLoading(true);
      setIncidentsError(null);
      try {
        const response: PaginatedResponse<Incident> = await buildingsApi.getIncidents(id, {
          page,
          page_size: pageSize,
        });
        setIncidents(response.items);
        setIncidentsPagination({
          page: response.page,
          pageSize: response.page_size,
          total: response.total,
          totalPages: response.total_pages,
        });
      } catch (err) {
        setIncidentsError(
          err instanceof Error ? err.message : 'Failed to fetch incidents'
        );
      } finally {
        setIncidentsLoading(false);
      }
    },
    [id]
  );

  // Load building data on mount
  useEffect(() => {
    if (!id) return;
    fetchBuilding(id);
    fetchFloorPlans(id);
    fetchBuildingAlerts(id);
    fetchIncidents(1, 10);

    return () => {
      reset();
    };
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Get unplaced devices for the current floor's building
  const unplacedDevices = devices.filter(
    (d) => d.position_x == null || d.position_y == null
  );

  // Handle floor plan upload complete
  const handleUploadComplete = useCallback(
    (newFloorPlan: typeof floorPlans[0]) => {
      addFloorPlan(newFloorPlan);
      setSubTab('alerts');
    },
    [addFloorPlan]
  );

  // Handle markers saved in FloorPlanEditor
  const handleMarkersSaved = useCallback(
    (markers: FloorKeyLocation[]) => {
      // Refresh building data to get updated markers
      if (id) {
        fetchFloorPlans(id);
      }
      console.log('Markers saved:', markers.length, 'markers');
    },
    [id, fetchFloorPlans]
  );

  if (isLoading && !building) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error && !building) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-700">{error}</p>
          <Button variant="secondary" className="mt-3" onClick={() => navigate('/buildings')}>
            Back to Buildings
          </Button>
        </div>
      </div>
    );
  }

  if (!building) return null;

  const hazardStyle = hazardLevelConfig[building.hazard_level];
  const typeLabel = buildingTypeLabels[building.building_type] || building.building_type;

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-gray-500 mb-4">
        <Link to="/buildings" className="hover:text-blue-600 transition-colors">
          Buildings
        </Link>
        <span>/</span>
        <span className="text-gray-900 font-medium">{building.name}</span>
      </nav>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{building.name}</h1>
          <p className="text-gray-500 mt-0.5">{building.full_address}</p>
          <div className="flex flex-wrap gap-2 mt-2">
            <Badge variant="secondary">{typeLabel}</Badge>
            <Badge className={cn(hazardStyle.bgColor, hazardStyle.color)}>
              {building.hazard_level} hazard
            </Badge>
            {building.is_verified ? (
              <Badge className="bg-green-100 text-green-700">Verified</Badge>
            ) : (
              <Badge variant="secondary">Unverified</Badge>
            )}
            {alertCount > 0 && (
              <Badge className="bg-red-100 text-red-700">
                {alertCount} active alert{alertCount !== 1 ? 's' : ''}
              </Badge>
            )}
          </div>
        </div>
        <Button variant="secondary" onClick={() => navigate('/buildings')}>
          Back
        </Button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center justify-between">
          <span className="text-red-700 text-sm">{error}</span>
          <button onClick={clearError} className="text-red-500 hover:text-red-700 text-sm">
            Dismiss
          </button>
        </div>
      )}

      {/* Two-column layout */}
      <div className="flex gap-6">
        {/* LEFT SIDEBAR */}
        <div className="w-80 flex-shrink-0 space-y-4">
          {/* Building Info */}
          <div className="border rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">Building Info</h3>
            <BuildingInfoPanel building={building} />
          </div>

          {/* Device Panel */}
          {selectedFloor && (
            <DeviceMonitoringPanel
              devices={devices}
              selectedDeviceId={selectedDevice?.id}
              onDeviceClick={setSelectedDevice}
            />
          )}

          {/* Actions */}
          <div className="border rounded-lg p-4 space-y-2">
            <h3 className="text-sm font-semibold text-gray-800 mb-2">Actions</h3>
            <Button
              variant="secondary"
              size="sm"
              className="w-full"
              onClick={() => setSubTab('upload')}
            >
              Upload Floor Plan
            </Button>
            {unplacedDevices.length > 0 && selectedFloor && (
              <div className="space-y-1.5">
                <p className="text-xs text-gray-500">
                  {unplacedDevices.length} unplaced device{unplacedDevices.length !== 1 ? 's' : ''}
                </p>
                {unplacedDevices.map((device) => (
                  <button
                    key={device.id}
                    onClick={() => {
                      if (isPlacementMode && placementDeviceId === device.id) {
                        exitPlacementMode();
                      } else {
                        enterPlacementMode(device.id);
                      }
                    }}
                    className={cn(
                      'w-full text-left px-3 py-1.5 text-sm rounded transition-colors',
                      isPlacementMode && placementDeviceId === device.id
                        ? 'bg-orange-100 text-orange-700 border border-orange-300'
                        : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                    )}
                  >
                    <span className="font-medium">{device.name}</span>
                    <span className="text-xs text-gray-400 ml-1">({device.device_type})</span>
                    {isPlacementMode && placementDeviceId === device.id && (
                      <span className="text-xs block text-orange-600">Click floor plan to place</span>
                    )}
                  </button>
                ))}
              </div>
            )}
            {isPlacementMode && (
              <Button
                variant="ghost"
                size="sm"
                className="w-full"
                onClick={exitPlacementMode}
              >
                Cancel Placement
              </Button>
            )}
          </div>
        </div>

        {/* MAIN CONTENT */}
        <div className="flex-1 min-w-0 space-y-4">
          {/* Floor Selector */}
          <FloorSelector
            floorPlans={floorPlans}
            selectedFloorId={selectedFloor?.id || null}
            onSelectFloor={selectFloor}
          />

          {/* Floor Plan Editor */}
          {selectedFloor ? (
            <div className="border rounded-lg overflow-hidden" style={{ height: '500px' }}>
              <FloorPlanEditor
                floorPlan={selectedFloor}
                building={building}
                initialMarkers={selectedFloor.key_locations || []}
                onSave={handleMarkersSaved}
              />
            </div>
          ) : (
            <div className="border rounded-lg p-12 text-center text-gray-400">
              {floorPlans.length === 0 ? (
                <>
                  <svg
                    className="w-16 h-16 mx-auto mb-4 text-gray-300"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
                    />
                  </svg>
                  <p>No floor plans uploaded yet</p>
                  <Button className="mt-4" onClick={() => setSubTab('upload')}>
                    Upload Floor Plan
                  </Button>
                </>
              ) : (
                <p>Select a floor to view its plan</p>
              )}
            </div>
          )}

          {/* Sub-tabs */}
          <div className="flex border-b">
            <button
              onClick={() => setSubTab('alerts')}
              className={cn(
                'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
                subTab === 'alerts'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              )}
            >
              Alerts
              {alerts.length > 0 && (
                <span className="ml-1.5 px-1.5 py-0.5 text-xs rounded-full bg-red-100 text-red-700">
                  {alerts.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setSubTab('incidents')}
              className={cn(
                'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
                subTab === 'incidents'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              )}
            >
              Incidents
              {incidentsPagination.total > 0 && (
                <span className="ml-1.5 px-1.5 py-0.5 text-xs rounded-full bg-blue-100 text-blue-700">
                  {incidentsPagination.total}
                </span>
              )}
            </button>
            <button
              onClick={() => setSubTab('upload')}
              className={cn(
                'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
                subTab === 'upload'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              )}
            >
              Upload Plan
            </button>
          </div>

          {/* Sub-tab content */}
          {subTab === 'alerts' && (
            <AlertsFloorTable
              alerts={alerts}
              isLoading={isLoadingAlerts}
            />
          )}

          {subTab === 'incidents' && (
            <IncidentHistoryTable
              incidents={incidents}
              isLoading={incidentsLoading}
              error={incidentsError}
              pagination={incidentsPagination}
              onPageChange={(page) => fetchIncidents(page, incidentsPagination.pageSize)}
            />
          )}

          {subTab === 'upload' && (
            <FloorPlanUpload
              buildingId={building.id}
              totalFloors={building.total_floors}
              basementLevels={building.basement_levels}
              existingFloorPlans={floorPlans}
              onUploadComplete={handleUploadComplete}
            />
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Incident History Table Component
 * Displays a paginated list of incidents related to this building.
 */
interface IncidentHistoryTableProps {
  incidents: Incident[];
  isLoading: boolean;
  error: string | null;
  pagination: {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
  };
  onPageChange: (page: number) => void;
}

function IncidentHistoryTable({
  incidents,
  isLoading,
  error,
  pagination,
  onPageChange,
}: IncidentHistoryTableProps) {
  const navigate = useNavigate();

  // Get incident type badge styling
  const getIncidentTypeBadgeClass = (type: string) => {
    const typeColors: Record<string, string> = {
      fire: 'bg-red-100 text-red-800 border-red-200',
      medical: 'bg-pink-100 text-pink-800 border-pink-200',
      police: 'bg-blue-100 text-blue-800 border-blue-200',
      traffic: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      hazmat: 'bg-orange-100 text-orange-800 border-orange-200',
      rescue: 'bg-purple-100 text-purple-800 border-purple-200',
      other: 'bg-gray-100 text-gray-800 border-gray-200',
    };
    return typeColors[type] || typeColors.other;
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border p-8 text-center">
        <Spinner size="md" />
        <p className="mt-2 text-gray-500">Loading incidents...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg border p-8 text-center">
        <p className="text-red-600">{error}</p>
      </div>
    );
  }

  if (incidents.length === 0) {
    return (
      <div className="bg-white rounded-lg border p-8 text-center text-gray-400">
        <svg
          className="w-12 h-12 mx-auto mb-3 text-gray-300"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <p>No incidents found for this building</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Incident #
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Type
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Title
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Status
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Reported
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {incidents.map((incident) => (
            <tr key={incident.id} className="hover:bg-gray-50">
              <td className="px-4 py-3 text-sm font-medium text-blue-600">
                <Link
                  to={`/incidents/${incident.id}`}
                  className="hover:text-blue-800 hover:underline"
                >
                  {incident.incident_number}
                </Link>
              </td>
              <td className="px-4 py-3">
                <span
                  className={cn(
                    'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border',
                    getIncidentTypeBadgeClass(incident.incident_type)
                  )}
                >
                  {getIncidentTypeLabel(incident.incident_type)}
                </span>
              </td>
              <td className="px-4 py-3 text-sm text-gray-700 max-w-xs truncate">
                {incident.title}
              </td>
              <td className="px-4 py-3">
                <Badge
                  className={cn(
                    getStatusBgColor(incident.status),
                    getStatusColor(incident.status)
                  )}
                >
                  {getStatusLabel(incident.status)}
                </Badge>
              </td>
              <td className="px-4 py-3 text-sm text-gray-500">
                {formatDate(incident.reported_at)}
              </td>
              <td className="px-4 py-3">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => navigate(`/incidents/${incident.id}`)}
                >
                  View
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Pagination */}
      {pagination.totalPages > 1 && (
        <div className="px-4 py-3 bg-gray-50 border-t flex items-center justify-between">
          <p className="text-sm text-gray-500">
            Showing {(pagination.page - 1) * pagination.pageSize + 1} to{' '}
            {Math.min(pagination.page * pagination.pageSize, pagination.total)} of{' '}
            {pagination.total} incidents
          </p>
          <div className="flex gap-1">
            <Button
              variant="secondary"
              size="sm"
              disabled={pagination.page <= 1}
              onClick={() => onPageChange(pagination.page - 1)}
            >
              Previous
            </Button>
            {/* Page numbers */}
            {Array.from({ length: Math.min(5, pagination.totalPages) }, (_, i) => {
              // Show pages around current page
              let pageNum: number;
              if (pagination.totalPages <= 5) {
                pageNum = i + 1;
              } else if (pagination.page <= 3) {
                pageNum = i + 1;
              } else if (pagination.page >= pagination.totalPages - 2) {
                pageNum = pagination.totalPages - 4 + i;
              } else {
                pageNum = pagination.page - 2 + i;
              }
              return (
                <Button
                  key={pageNum}
                  variant={pageNum === pagination.page ? 'primary' : 'secondary'}
                  size="sm"
                  onClick={() => onPageChange(pageNum)}
                  className="min-w-[36px]"
                >
                  {pageNum}
                </Button>
              );
            })}
            <Button
              variant="secondary"
              size="sm"
              disabled={pagination.page >= pagination.totalPages}
              onClick={() => onPageChange(pagination.page + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
