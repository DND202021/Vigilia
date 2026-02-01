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

import React, { useEffect, useState, useCallback, Suspense, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useBuildingDetailStore } from '../stores/buildingDetailStore';
import { useInspectionStore } from '../stores/inspectionStore';
import { useDocumentStore } from '../stores/documentStore';
import { usePhotoStore } from '../stores/photoStore';
import { useWebSocket } from '../hooks/useWebSocket';
import { FloorSelector } from '../components/buildings/FloorSelector';
import { BuildingInfoPanel } from '../components/buildings/BuildingInfoPanel';
import { FloorPlanEditor } from '../components/buildings/FloorPlanEditor';
import { FloorPlanUpload, BIMImport, BIMDataViewer, BuildingEditModal, FloorPlanManageModal } from '../components/buildings';
import { BuildingAnalyticsDashboard } from '../components/analytics';
import { DeviceMonitoringPanel } from '../components/devices/DeviceMonitoringPanel';
import { DeviceDetailPanel } from '../components/devices/DeviceDetailPanel';
import { DeviceConfigEditor } from '../components/devices/DeviceConfigEditor';
import { DevicePlacementEditor } from '../components/devices/DevicePlacementEditor';
import { AlertsFloorTable } from '../components/alerts/AlertsFloorTable';
import {
  EmergencyPlanViewer,
  EmergencyProcedureEditor,
  EvacuationRouteDrawer,
  CheckpointManager
} from '../components/emergency';
import { useDeviceStore } from '../stores/deviceStore';
import { iotDevicesApi, emergencyPlanningApi } from '../services/api';
import type { IoTDevice, EmergencyPlanOverview, EmergencyProcedure, EmergencyCheckpoint, RouteWaypoint } from '../types';
import { Badge, Button, Spinner } from '../components/ui';
import { toast } from '../stores/toastStore';
import {
  cn,
  formatDate,
  getIncidentTypeLabel,
  getStatusLabel,
  getStatusBgColor,
  getStatusColor,
} from '../utils';
import { buildingsApi } from '../services/api';
import type { FloorKeyLocation, FloorPlan, HazardLevel, Incident, PaginatedResponse, BIMImportResult } from '../types';

// Lazy load Sprint 6 components for code splitting
const DocumentManager = React.lazy(() => import('../components/buildings/DocumentManager'));
const PhotoGallery = React.lazy(() => import('../components/buildings/PhotoGallery'));
const PhotoCapture = React.lazy(() => import('../components/buildings/PhotoCapture'));
const InspectionTracker = React.lazy(() => import('../components/buildings/InspectionTracker'));

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

type SubTab = 'alerts' | 'incidents' | 'upload' | 'bim' | 'documents' | 'photos' | 'inspections' | 'devices' | 'analytics' | 'emergency';

/**
 * ConnectionStatusIndicator
 * Small colored dot showing WebSocket connection state
 */
function ConnectionStatusIndicator({ isConnected }: { isConnected: boolean }) {
  return (
    <div className="flex items-center gap-1.5" title={isConnected ? 'Real-time updates active' : 'Real-time updates unavailable'}>
      <span
        className={cn(
          'w-2 h-2 rounded-full',
          isConnected ? 'bg-green-500' : 'bg-gray-400'
        )}
      />
      <span className="text-xs text-gray-500">
        {isConnected ? 'Live' : 'Offline'}
      </span>
    </div>
  );
}

/**
 * RemoteUpdateNotification
 * Subtle notification when remote changes occur
 */
function RemoteUpdateNotification({
  message,
  onDismiss
}: {
  message: string;
  onDismiss: () => void;
}) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 5000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <div className="fixed bottom-4 right-4 z-50 animate-in slide-in-from-bottom-2 fade-in duration-200">
      <div className="bg-blue-600 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-3">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="text-sm">{message}</span>
        <button onClick={onDismiss} className="ml-2 text-blue-200 hover:text-white">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}

export function BuildingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // WebSocket hook for real-time updates
  const {
    isConnected,
    lastEvent,
    connect,
    joinBuilding,
    leaveBuilding,
  } = useWebSocket();

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

  // Document and photo stores for real-time refresh
  const fetchDocuments = useDocumentStore((state) => state.fetchDocuments);
  const fetchPhotos = usePhotoStore((state) => state.fetchPhotos);

  const [subTab, setSubTab] = useState<SubTab>('alerts');

  // BIM tab state - track whether showing import form vs viewer
  const [showBIMImport, setShowBIMImport] = useState(false);

  // PhotoCapture modal state
  const [showPhotoCapture, setShowPhotoCapture] = useState(false);

  // Device management state
  const [selectedDeviceForPanel, setSelectedDeviceForPanel] = useState<IoTDevice | null>(null);
  const [showDeviceConfig, setShowDeviceConfig] = useState(false);
  const [showPlacementEditor, setShowPlacementEditor] = useState(false);

  // Emergency planning state
  const [emergencyPlan, setEmergencyPlan] = useState<EmergencyPlanOverview | null>(null);
  const [emergencyPlanLoading, setEmergencyPlanLoading] = useState(false);
  const [isEditingEmergencyPlan, setIsEditingEmergencyPlan] = useState(false);
  const [editingProcedure, setEditingProcedure] = useState<EmergencyProcedure | undefined>();
  const [emergencyEditMode, setEmergencyEditMode] = useState<'view' | 'procedures' | 'routes' | 'checkpoints'>('view');
  const [selectedRouteId, setSelectedRouteId] = useState<string | undefined>();
  const [selectedCheckpointId, setSelectedCheckpointId] = useState<string | undefined>();

  // Building edit modal state
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isFloorPlanManageOpen, setIsFloorPlanManageOpen] = useState(false);

  // Device store for the Devices tab
  const {
    devices: buildingDevices,
    totalDevices: totalBuildingDevices,
    isLoading: isLoadingDevices,
    fetchDevices: fetchBuildingDevices,
    deleteDevice,
    updatePosition,
  } = useDeviceStore();

  // Remote update notification state
  const [remoteNotification, setRemoteNotification] = useState<string | null>(null);

  // Track previous lastEvent to detect changes
  const prevLastEventRef = useRef<string | null>(null);

  // Get inspection counts for alert badges
  const {
    inspections,
    fetchInspections: fetchBuildingInspections,
  } = useInspectionStore();

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

  // Fetch emergency plan data for the building
  const fetchEmergencyPlan = useCallback(async () => {
    if (!building?.id) return;
    setEmergencyPlanLoading(true);
    try {
      const plan = await emergencyPlanningApi.getEmergencyPlan(building.id);
      setEmergencyPlan(plan);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch emergency plan';
      if (message === 'Network Error') {
        toast.error('Unable to load emergency plan. Server is unavailable.');
      }
      // Non-critical, don't show toast for other errors
    } finally {
      setEmergencyPlanLoading(false);
    }
  }, [building?.id]);

  // Load building data on mount
  useEffect(() => {
    if (!id) return;
    fetchBuilding(id);
    fetchFloorPlans(id);
    fetchBuildingAlerts(id);
    fetchIncidents(1, 10);
    fetchBuildingInspections(id);
    fetchBuildingDevices({ building_id: id });

    return () => {
      reset();
    };
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Connect to WebSocket on mount
  useEffect(() => {
    connect();
  }, [connect]);

  // Join/leave building WebSocket room for real-time updates
  useEffect(() => {
    if (id && isConnected) {
      joinBuilding(id);
    }
    return () => {
      if (id) {
        leaveBuilding(id);
      }
    };
  }, [id, isConnected, joinBuilding, leaveBuilding]);

  // Lazy load emergency plan data when tab is active
  useEffect(() => {
    if (subTab === 'emergency' && building?.id && !emergencyPlan && !emergencyPlanLoading) {
      fetchEmergencyPlan();
    }
  }, [subTab, building?.id, emergencyPlan, emergencyPlanLoading, fetchEmergencyPlan]);

  // Handle incoming WebSocket events for this building
  useEffect(() => {
    if (!lastEvent || lastEvent === prevLastEventRef.current) return;
    prevLastEventRef.current = lastEvent;

    // Parse the event type and id
    const [eventType, eventSubType, eventId] = lastEvent.split(':');
    const fullEventType = `${eventType}:${eventSubType}`;

    // Only handle events for the current building
    if (!id) return;

    switch (fullEventType) {
      case 'building:updated':
        // Refresh building data when updated remotely
        if (eventId === id) {
          fetchBuilding(id);
          setRemoteNotification('Building information was updated');
        }
        break;

      case 'floor_plan:uploaded':
        // Floor plan added - the useWebSocket hook already handles adding it to the store
        // Just show notification
        setRemoteNotification('A new floor plan was uploaded');
        break;

      case 'floor_plan:updated':
        // Floor plan updated - refresh floor plans
        fetchFloorPlans(id);
        setRemoteNotification('Floor plan was updated');
        break;

      case 'markers:updated':
        // Markers updated - the useWebSocket hook handles this
        setRemoteNotification('Floor plan markers were updated');
        break;

      case 'document:uploaded':
      case 'document:updated':
      case 'document:deleted':
        // Refresh documents list if on documents tab
        if (subTab === 'documents') {
          fetchDocuments(id);
        }
        setRemoteNotification('Documents were updated');
        break;

      case 'photo:uploaded':
      case 'photo:deleted':
        // Refresh photos list if on photos tab
        if (subTab === 'photos') {
          fetchPhotos(id);
        }
        setRemoteNotification('Photos were updated');
        break;

      case 'inspection:created':
      case 'inspection:updated':
      case 'inspection:deleted':
        // Refresh inspections list if on inspections tab
        if (subTab === 'inspections') {
          fetchBuildingInspections(id);
        }
        setRemoteNotification('Inspections were updated');
        break;

      case 'device:created':
      case 'device:updated':
      case 'device:deleted':
        // Refresh devices list if on devices tab
        if (subTab === 'devices') {
          fetchBuildingDevices({ building_id: id });
        }
        setRemoteNotification('Devices were updated');
        break;

      case 'procedure:created':
      case 'procedure:updated':
      case 'procedure:deleted':
      case 'route:created':
      case 'route:updated':
      case 'route:deleted':
      case 'checkpoint:created':
      case 'checkpoint:updated':
      case 'checkpoint:deleted':
        // Refresh emergency plan if on emergency tab
        if (subTab === 'emergency') {
          fetchEmergencyPlan();
        }
        setRemoteNotification('Emergency plan was updated');
        break;

      default:
        // Ignore other events
        break;
    }
  }, [lastEvent, id, fetchBuilding, fetchFloorPlans, fetchDocuments, fetchPhotos, fetchBuildingInspections, fetchBuildingDevices, fetchEmergencyPlan, subTab]);

  // Compute upcoming and overdue inspection counts
  const upcomingInspectionCount = inspections.filter((i) => {
    if (i.status === 'completed' || i.status === 'failed') return false;
    const scheduledDate = new Date(i.scheduled_date);
    const today = new Date();
    const sevenDaysFromNow = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
    return scheduledDate >= today && scheduledDate <= sevenDaysFromNow;
  }).length;

  const overdueInspectionCount = inspections.filter((i) => {
    if (i.status === 'completed' || i.status === 'failed') return false;
    return new Date(i.scheduled_date) < new Date();
  }).length;

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

  // Handle BIM import completion
  const handleBIMImportComplete = useCallback(
    (result: BIMImportResult) => {
      // Refresh building data to get updated BIM data
      if (id) {
        fetchBuilding(id);
        // BIM import may create floor plans, so refresh those too
        fetchFloorPlans(id);
      }
      // Switch to showing BIMDataViewer instead of import form
      setShowBIMImport(false);
      console.log('BIM import complete:', result.floors_created, 'floors created');
    },
    [id, fetchBuilding, fetchFloorPlans]
  );

  // ========== Emergency Plan CRUD Handlers ==========

  // Handle procedure save (create or update)
  const handleProcedureSave = useCallback(async (procedure: EmergencyProcedure) => {
    if (!building?.id) return;
    try {
      if (procedure.id) {
        // Update existing
        await emergencyPlanningApi.updateProcedure(procedure.id, procedure);
      } else {
        // Create new
        await emergencyPlanningApi.createProcedure(building.id, procedure);
      }
      await fetchEmergencyPlan();
      setEditingProcedure(undefined);
      setEmergencyEditMode('view');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to save procedure';
      toast.error(message === 'Network Error' ? 'Unable to save. Server is unavailable.' : message);
    }
  }, [building?.id, fetchEmergencyPlan]);

  // Handle procedure delete
  const handleProcedureDelete = useCallback(async (procedureId: string) => {
    if (!window.confirm('Are you sure you want to delete this procedure?')) return;
    try {
      await emergencyPlanningApi.deleteProcedure(procedureId);
      await fetchEmergencyPlan();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to delete procedure';
      toast.error(message === 'Network Error' ? 'Unable to delete. Server is unavailable.' : message);
    }
  }, [fetchEmergencyPlan]);

  // Handle route create from waypoints
  const handleRouteCreate = useCallback(async (waypoints: RouteWaypoint[]) => {
    if (!building?.id || !selectedFloor?.id) return;
    try {
      await emergencyPlanningApi.createRoute(building.id, {
        building_id: building.id,
        floor_plan_id: selectedFloor.id,
        name: `Route ${(emergencyPlan?.routes.length || 0) + 1}`,
        route_type: 'primary',
        waypoints,
        color: '#dc2626', // Default red color for primary routes
        line_width: 3,
        accessibility_features: [],
        is_active: true,
      });
      await fetchEmergencyPlan();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to create route';
      toast.error(message === 'Network Error' ? 'Unable to create route. Server is unavailable.' : message);
    }
  }, [building?.id, selectedFloor?.id, emergencyPlan?.routes.length, fetchEmergencyPlan]);

  // Handle route update
  const handleRouteUpdate = useCallback(async (routeId: string, waypoints: RouteWaypoint[]) => {
    try {
      await emergencyPlanningApi.updateRoute(routeId, { waypoints });
      await fetchEmergencyPlan();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to update route';
      toast.error(message === 'Network Error' ? 'Unable to update route. Server is unavailable.' : message);
    }
  }, [fetchEmergencyPlan]);

  // Handle route delete
  const handleRouteDelete = useCallback(async (routeId: string) => {
    if (!window.confirm('Are you sure you want to delete this route?')) return;
    try {
      await emergencyPlanningApi.deleteRoute(routeId);
      await fetchEmergencyPlan();
      setSelectedRouteId(undefined);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to delete route';
      toast.error(message === 'Network Error' ? 'Unable to delete route. Server is unavailable.' : message);
    }
  }, [fetchEmergencyPlan]);

  // Handle checkpoint create
  const handleCheckpointCreate = useCallback(async (checkpoint: Omit<EmergencyCheckpoint, 'id' | 'created_at' | 'updated_at'>) => {
    if (!building?.id) return;
    try {
      await emergencyPlanningApi.createCheckpoint(building.id, {
        ...checkpoint,
        building_id: building.id,
      });
      await fetchEmergencyPlan();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to create checkpoint';
      toast.error(message === 'Network Error' ? 'Unable to create checkpoint. Server is unavailable.' : message);
    }
  }, [building?.id, fetchEmergencyPlan]);

  // Handle checkpoint update
  const handleCheckpointUpdate = useCallback(async (checkpointId: string, data: Partial<EmergencyCheckpoint>) => {
    try {
      await emergencyPlanningApi.updateCheckpoint(checkpointId, data);
      await fetchEmergencyPlan();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to update checkpoint';
      toast.error(message === 'Network Error' ? 'Unable to update checkpoint. Server is unavailable.' : message);
    }
  }, [fetchEmergencyPlan]);

  // Handle checkpoint delete
  const handleCheckpointDelete = useCallback(async (checkpointId: string) => {
    if (!window.confirm('Are you sure you want to delete this checkpoint?')) return;
    try {
      await emergencyPlanningApi.deleteCheckpoint(checkpointId);
      await fetchEmergencyPlan();
      setSelectedCheckpointId(undefined);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to delete checkpoint';
      toast.error(message === 'Network Error' ? 'Unable to delete checkpoint. Server is unavailable.' : message);
    }
  }, [fetchEmergencyPlan]);

  // Handle emergency plan print
  const handleEmergencyPlanPrint = useCallback(() => {
    console.log('Printing emergency plan...');
  }, []);

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
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">{building.name}</h1>
            <ConnectionStatusIndicator isConnected={isConnected} />
          </div>
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
            {overdueInspectionCount > 0 && (
              <Badge className="bg-red-100 text-red-700 animate-pulse">
                {overdueInspectionCount} overdue inspection{overdueInspectionCount !== 1 ? 's' : ''}
              </Badge>
            )}
            {upcomingInspectionCount > 0 && (
              <Badge className="bg-amber-100 text-amber-700">
                {upcomingInspectionCount} upcoming inspection{upcomingInspectionCount !== 1 ? 's' : ''}
              </Badge>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setIsEditModalOpen(true)}>
            Edit
          </Button>
          <Button variant="secondary" onClick={() => navigate('/buildings')}>
            Back
          </Button>
        </div>
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
            {floorPlans.length > 0 && (
              <Button
                variant="secondary"
                size="sm"
                className="w-full"
                onClick={() => setIsFloorPlanManageOpen(true)}
              >
                Manage Floor Plans
              </Button>
            )}
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
            <button
              onClick={() => setSubTab('bim')}
              className={cn(
                'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
                subTab === 'bim'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              )}
            >
              BIM Data
              {building.has_bim_data && (
                <span className="ml-1.5 px-1.5 py-0.5 text-xs rounded-full bg-green-100 text-green-700">
                  Imported
                </span>
              )}
            </button>
            <button
              onClick={() => setSubTab('documents')}
              className={cn(
                'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
                subTab === 'documents'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              )}
            >
              Documents
            </button>
            <button
              onClick={() => setSubTab('photos')}
              className={cn(
                'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
                subTab === 'photos'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              )}
            >
              Photos
            </button>
            <button
              onClick={() => setSubTab('inspections')}
              className={cn(
                'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
                subTab === 'inspections'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              )}
            >
              Inspections
              {(overdueInspectionCount > 0 || upcomingInspectionCount > 0) && (
                <span className={cn(
                  'ml-1.5 px-1.5 py-0.5 text-xs rounded-full',
                  overdueInspectionCount > 0 ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                )}>
                  {overdueInspectionCount > 0 ? overdueInspectionCount : upcomingInspectionCount}
                </span>
              )}
            </button>
            <button
              onClick={() => setSubTab('devices')}
              className={cn(
                'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
                subTab === 'devices'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              )}
            >
              Devices
              {totalBuildingDevices > 0 && (
                <span className="ml-1.5 px-1.5 py-0.5 text-xs rounded-full bg-blue-100 text-blue-700">
                  {totalBuildingDevices}
                </span>
              )}
            </button>
            <button
              onClick={() => setSubTab('analytics')}
              className={cn(
                'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
                subTab === 'analytics'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              )}
            >
              Analytics
            </button>
            <button
              onClick={() => setSubTab('emergency')}
              className={cn(
                'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors flex items-center gap-1.5',
                subTab === 'emergency'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              )}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              Emergency
              {emergencyPlan && (emergencyPlan.procedures.length > 0 || emergencyPlan.routes.length > 0) && (
                <span className="px-1.5 py-0.5 text-xs rounded-full bg-green-100 text-green-700">
                  {emergencyPlan.procedures.length + emergencyPlan.routes.length}
                </span>
              )}
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

          {subTab === 'bim' && (
            <div className="space-y-4">
              {/* Show BIMDataViewer if building has BIM data and not in import mode */}
              {building.has_bim_data && !showBIMImport ? (
                <>
                  <BIMDataViewer building={building} />
                  <div className="flex justify-end">
                    <button
                      onClick={() => setShowBIMImport(true)}
                      className="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
                    >
                      Re-import BIM Data
                    </button>
                  </div>
                </>
              ) : (
                /* Show BIMImport if no BIM data or user requested re-import */
                <BIMImport
                  buildingId={building.id}
                  onImportComplete={handleBIMImportComplete}
                  onCancel={building.has_bim_data ? () => setShowBIMImport(false) : undefined}
                />
              )}
            </div>
          )}

          {subTab === 'documents' && (
            <Suspense fallback={<div className="flex items-center justify-center py-12"><Spinner size="md" /></div>}>
              <DocumentManager buildingId={building.id} />
            </Suspense>
          )}

          {subTab === 'photos' && (
            <Suspense fallback={<div className="flex items-center justify-center py-12"><Spinner size="md" /></div>}>
              <PhotoGallery
                buildingId={building.id}
                floorPlanId={selectedFloor?.id}
                onCaptureClick={() => setShowPhotoCapture(true)}
              />
            </Suspense>
          )}

          {subTab === 'inspections' && (
            <Suspense fallback={<div className="flex items-center justify-center py-12"><Spinner size="md" /></div>}>
              <InspectionTracker buildingId={building.id} />
            </Suspense>
          )}

          {subTab === 'devices' && (
            <DevicesTabContent
              devices={buildingDevices}
              totalDevices={totalBuildingDevices}
              isLoading={isLoadingDevices}
              selectedDevice={selectedDeviceForPanel}
              onSelectDevice={setSelectedDeviceForPanel}
              onEditDevice={() => {
                // Edit handled by DeviceDetailPanel's onEdit
              }}
              onConfigureDevice={() => setShowDeviceConfig(true)}
              onDeleteDevice={async (deviceId: string) => {
                if (window.confirm('Are you sure you want to delete this device?')) {
                  await deleteDevice(deviceId);
                  setSelectedDeviceForPanel(null);
                }
              }}
              onCloseDetailPanel={() => setSelectedDeviceForPanel(null)}
              showPlacementEditor={showPlacementEditor}
              onTogglePlacementEditor={() => setShowPlacementEditor(!showPlacementEditor)}
              selectedFloor={selectedFloor}
              onSavePosition={async (deviceId: string, x: number, y: number, floorPlanId: string) => {
                await updatePosition(deviceId, {
                  floor_plan_id: floorPlanId,
                  position_x: x,
                  position_y: y,
                });
              }}
            />
          )}

          {subTab === 'analytics' && id && (
            <BuildingAnalyticsDashboard buildingId={id} />
          )}

          {subTab === 'emergency' && (
            <EmergencyTabContent
              buildingId={building.id}
              buildingName={building.name}
              floorPlans={floorPlans}
              selectedFloor={selectedFloor}
              emergencyPlan={emergencyPlan}
              isLoading={emergencyPlanLoading}
              isEditing={isEditingEmergencyPlan}
              editMode={emergencyEditMode}
              editingProcedure={editingProcedure}
              selectedRouteId={selectedRouteId}
              selectedCheckpointId={selectedCheckpointId}
              onEditToggle={() => setIsEditingEmergencyPlan(!isEditingEmergencyPlan)}
              onEditModeChange={setEmergencyEditMode}
              onProcedureEdit={(procedure) => {
                setEditingProcedure(procedure);
                setEmergencyEditMode('procedures');
              }}
              onProcedureSave={handleProcedureSave}
              onProcedureCancel={() => {
                setEditingProcedure(undefined);
                setEmergencyEditMode('view');
              }}
              onProcedureDelete={handleProcedureDelete}
              onRouteCreate={handleRouteCreate}
              onRouteUpdate={handleRouteUpdate}
              onRouteDelete={handleRouteDelete}
              onRouteSelect={setSelectedRouteId}
              onCheckpointCreate={handleCheckpointCreate}
              onCheckpointUpdate={handleCheckpointUpdate}
              onCheckpointDelete={handleCheckpointDelete}
              onCheckpointSelect={setSelectedCheckpointId}
              onPrint={handleEmergencyPlanPrint}
              onRefresh={fetchEmergencyPlan}
            />
          )}
        </div>
      </div>

      {/* PhotoCapture Modal */}
      {showPhotoCapture && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="max-w-2xl w-full">
            <Suspense fallback={<div className="bg-white rounded-lg p-8 flex items-center justify-center"><Spinner size="md" /></div>}>
              <PhotoCapture
                buildingId={building.id}
                floorPlanId={selectedFloor?.id}
                onClose={() => setShowPhotoCapture(false)}
                onCapture={() => {
                  setShowPhotoCapture(false);
                  // The photo store will automatically refresh the photos list
                }}
              />
            </Suspense>
          </div>
        </div>
      )}

      {/* DeviceConfigEditor Modal */}
      {showDeviceConfig && selectedDeviceForPanel && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="max-w-xl w-full max-h-[90vh] overflow-y-auto">
            <DeviceConfigEditor
              device={selectedDeviceForPanel}
              onSave={async (config) => {
                await iotDevicesApi.updateConfig(selectedDeviceForPanel.id, config);
                // Refresh device list
                if (id) {
                  fetchBuildingDevices({ building_id: id });
                }
                setShowDeviceConfig(false);
              }}
              onCancel={() => setShowDeviceConfig(false)}
            />
          </div>
        </div>
      )}

      {/* Remote Update Notification */}
      {remoteNotification && (
        <RemoteUpdateNotification
          message={remoteNotification}
          onDismiss={() => setRemoteNotification(null)}
        />
      )}

      {/* Building Edit Modal */}
      <BuildingEditModal
        building={building}
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        onSaved={() => {
          if (id) {
            fetchBuilding(id);
          }
        }}
      />

      {/* Floor Plan Management Modal */}
      <FloorPlanManageModal
        buildingId={building.id}
        floorPlans={floorPlans}
        isOpen={isFloorPlanManageOpen}
        onClose={() => setIsFloorPlanManageOpen(false)}
        onUpdated={() => {
          if (id) {
            fetchFloorPlans(id);
          }
        }}
      />
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

/**
 * Devices Tab Content Component
 * Displays devices in the building with management capabilities.
 */
interface DevicesTabContentProps {
  devices: IoTDevice[];
  totalDevices: number;
  isLoading: boolean;
  selectedDevice: IoTDevice | null;
  onSelectDevice: (device: IoTDevice | null) => void;
  onEditDevice: () => void;
  onConfigureDevice: () => void;
  onDeleteDevice: (deviceId: string) => Promise<void>;
  onCloseDetailPanel: () => void;
  showPlacementEditor: boolean;
  onTogglePlacementEditor: () => void;
  selectedFloor: FloorPlan | null;
  onSavePosition: (deviceId: string, x: number, y: number, floorPlanId: string) => Promise<void>;
}

function DevicesTabContent({
  devices,
  totalDevices,
  isLoading,
  selectedDevice,
  onSelectDevice,
  onEditDevice,
  onConfigureDevice,
  onDeleteDevice,
  onCloseDetailPanel,
  showPlacementEditor,
  onTogglePlacementEditor,
  selectedFloor,
  onSavePosition,
}: DevicesTabContentProps) {
  // Filter devices by current floor plan
  const floorDevices = selectedFloor
    ? devices.filter((d) => d.floor_plan_id === selectedFloor.id)
    : devices;

  // Get unplaced devices (no position set)
  const unplacedDevices = floorDevices.filter(
    (d) => d.position_x == null || d.position_y == null
  );

  // Get placed devices
  const placedDevices = floorDevices.filter(
    (d) => d.position_x != null && d.position_y != null
  );

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border p-8 text-center">
        <Spinner size="md" />
        <p className="mt-2 text-gray-500">Loading devices...</p>
      </div>
    );
  }

  // Show placement editor if active
  if (showPlacementEditor && selectedFloor && selectedFloor.plan_file_url) {
    return (
      <DevicePlacementEditor
        floorPlanUrl={selectedFloor.plan_file_url}
        floorPlanId={selectedFloor.id}
        devices={placedDevices}
        unplacedDevices={unplacedDevices}
        onSavePosition={onSavePosition}
        onCancel={onTogglePlacementEditor}
      />
    );
  }

  return (
    <div className="flex gap-4">
      {/* Main device list */}
      <div className="flex-1">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">IoT Devices</h3>
            <p className="text-sm text-gray-500">
              {totalDevices} device{totalDevices !== 1 ? 's' : ''} in this building
              {selectedFloor && ` (${floorDevices.length} on current floor)`}
            </p>
          </div>
          <div className="flex gap-2">
            {selectedFloor && (
              <Button
                variant="secondary"
                size="sm"
                onClick={onTogglePlacementEditor}
              >
                <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Edit Placement
              </Button>
            )}
          </div>
        </div>

        {/* Device list or empty state */}
        {devices.length === 0 ? (
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
                d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
              />
            </svg>
            <p>No devices in this building</p>
            <p className="text-sm mt-1">Add devices to monitor this building</p>
          </div>
        ) : (
          <DeviceMonitoringPanel
            devices={selectedFloor ? floorDevices : devices}
            selectedDeviceId={selectedDevice?.id}
            onDeviceClick={onSelectDevice}
            className="border-0 shadow-none"
          />
        )}
      </div>

      {/* Device detail panel (sidebar) */}
      {selectedDevice && (
        <div className="w-96 flex-shrink-0">
          <DeviceDetailPanel
            device={selectedDevice}
            onEdit={onEditDevice}
            onConfigure={onConfigureDevice}
            onDelete={() => onDeleteDevice(selectedDevice.id)}
            onClose={onCloseDetailPanel}
          />
        </div>
      )}
    </div>
  );
}

/**
 * Emergency Tab Content Component
 * Displays and manages emergency planning information for a building.
 */
interface EmergencyTabContentProps {
  buildingId: string;
  buildingName: string;
  floorPlans: FloorPlan[];
  selectedFloor: FloorPlan | null;
  emergencyPlan: EmergencyPlanOverview | null;
  isLoading: boolean;
  isEditing: boolean;
  editMode: 'view' | 'procedures' | 'routes' | 'checkpoints';
  editingProcedure: EmergencyProcedure | undefined;
  selectedRouteId: string | undefined;
  selectedCheckpointId: string | undefined;
  onEditToggle: () => void;
  onEditModeChange: (mode: 'view' | 'procedures' | 'routes' | 'checkpoints') => void;
  onProcedureEdit: (procedure: EmergencyProcedure) => void;
  onProcedureSave: (procedure: EmergencyProcedure) => void;
  onProcedureCancel: () => void;
  onProcedureDelete: (procedureId: string) => void;
  onRouteCreate: (waypoints: RouteWaypoint[]) => void;
  onRouteUpdate: (routeId: string, waypoints: RouteWaypoint[]) => void;
  onRouteDelete: (routeId: string) => void;
  onRouteSelect: (routeId: string | undefined) => void;
  onCheckpointCreate: (checkpoint: Omit<EmergencyCheckpoint, 'id' | 'created_at' | 'updated_at'>) => void;
  onCheckpointUpdate: (checkpointId: string, data: Partial<EmergencyCheckpoint>) => void;
  onCheckpointDelete: (checkpointId: string) => void;
  onCheckpointSelect: (checkpointId: string | undefined) => void;
  onPrint: () => void;
  onRefresh: () => void;
}

function EmergencyTabContent({
  buildingId,
  buildingName,
  floorPlans,
  selectedFloor,
  emergencyPlan,
  isLoading,
  isEditing,
  editMode,
  editingProcedure,
  selectedRouteId,
  selectedCheckpointId,
  onEditToggle,
  onEditModeChange,
  onProcedureEdit,
  onProcedureSave,
  onProcedureCancel,
  onProcedureDelete,
  onRouteCreate,
  onRouteUpdate,
  onRouteDelete,
  onRouteSelect,
  onCheckpointCreate,
  onCheckpointUpdate,
  onCheckpointDelete,
  onCheckpointSelect,
  onPrint,
  onRefresh,
}: EmergencyTabContentProps) {
  // Reference for floor plan container dimensions
  const floorPlanContainerRef = useRef<HTMLDivElement>(null);
  const [containerDimensions, setContainerDimensions] = useState({ width: 0, height: 0 });

  // Update container dimensions when floor changes
  useEffect(() => {
    const updateDimensions = () => {
      if (floorPlanContainerRef.current) {
        setContainerDimensions({
          width: floorPlanContainerRef.current.offsetWidth,
          height: floorPlanContainerRef.current.offsetHeight,
        });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, [selectedFloor]);

  // Loading state
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border p-8 text-center">
        <Spinner size="md" />
        <p className="mt-2 text-gray-500">Loading emergency plan...</p>
      </div>
    );
  }

  // Empty state
  if (!emergencyPlan || (emergencyPlan.procedures.length === 0 && emergencyPlan.routes.length === 0 && emergencyPlan.checkpoints.length === 0)) {
    return (
      <div className="bg-white rounded-lg border p-8 text-center">
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
            d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
          />
        </svg>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No Emergency Plan</h3>
        <p className="text-gray-500 mb-4">
          This building doesn't have an emergency plan yet. Start by adding procedures, evacuation routes, or checkpoints.
        </p>
        <Button onClick={onEditToggle}>
          Create Emergency Plan
        </Button>
      </div>
    );
  }

  // Prepare floor plan info for viewer
  const floorPlanInfo = floorPlans.map(fp => ({
    id: fp.id,
    name: fp.floor_name || `Floor ${fp.floor_number}`,
    floor_number: fp.floor_number,
    image_url: fp.plan_file_url || '',
  }));

  // View mode - show the viewer
  if (!isEditing) {
    return (
      <EmergencyPlanViewer
        buildingId={buildingId}
        buildingName={buildingName}
        floorPlans={floorPlanInfo}
        plan={emergencyPlan}
        onEdit={onEditToggle}
        onPrint={onPrint}
      />
    );
  }

  // Edit mode - show editing interface
  return (
    <div className="space-y-4">
      {/* Edit mode toolbar */}
      <div className="bg-white rounded-lg border p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold text-gray-900">Edit Emergency Plan</h3>
            <Badge className="bg-orange-100 text-orange-700">Editing</Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={onRefresh}>
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </Button>
            <Button variant="secondary" onClick={onEditToggle}>
              Done Editing
            </Button>
          </div>
        </div>

        {/* Edit mode sub-tabs */}
        <div className="flex gap-2">
          <button
            onClick={() => onEditModeChange('procedures')}
            className={cn(
              'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
              editMode === 'procedures'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            )}
          >
            Procedures ({emergencyPlan.procedures.length})
          </button>
          <button
            onClick={() => onEditModeChange('routes')}
            className={cn(
              'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
              editMode === 'routes'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            )}
          >
            Routes ({emergencyPlan.routes.length})
          </button>
          <button
            onClick={() => onEditModeChange('checkpoints')}
            className={cn(
              'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
              editMode === 'checkpoints'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            )}
          >
            Checkpoints ({emergencyPlan.checkpoints.length})
          </button>
        </div>
      </div>

      {/* Procedures edit mode */}
      {editMode === 'procedures' && (
        <div className="space-y-4">
          {editingProcedure !== undefined ? (
            <EmergencyProcedureEditor
              buildingId={buildingId}
              procedure={editingProcedure}
              onSave={onProcedureSave}
              onCancel={onProcedureCancel}
            />
          ) : (
            <>
              <div className="flex justify-between items-center">
                <h4 className="text-md font-medium text-gray-800">Emergency Procedures</h4>
                <Button
                  size="sm"
                  onClick={() => onProcedureEdit({
                    id: '',
                    building_id: buildingId,
                    name: '',
                    procedure_type: 'evacuation',
                    priority: 3,
                    is_active: true,
                    steps: [],
                    contacts: [],
                    equipment_needed: [],
                    created_at: '',
                    updated_at: '',
                  })}
                >
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Add Procedure
                </Button>
              </div>

              {emergencyPlan.procedures.length === 0 ? (
                <div className="bg-gray-50 rounded-lg p-8 text-center text-gray-500">
                  No procedures defined. Click "Add Procedure" to create one.
                </div>
              ) : (
                <div className="space-y-3">
                  {emergencyPlan.procedures.map((procedure) => (
                    <div
                      key={procedure.id}
                      className="bg-white rounded-lg border p-4 flex items-center justify-between"
                    >
                      <div>
                        <h5 className="font-medium text-gray-900">{procedure.name}</h5>
                        <p className="text-sm text-gray-500">
                          {procedure.procedure_type} - Priority {procedure.priority}
                          {procedure.steps.length > 0 && ` - ${procedure.steps.length} steps`}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onProcedureEdit(procedure)}
                        >
                          Edit
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-600 hover:text-red-700"
                          onClick={() => onProcedureDelete(procedure.id)}
                        >
                          Delete
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Routes edit mode */}
      {editMode === 'routes' && selectedFloor && selectedFloor.plan_file_url && (
        <div className="bg-white rounded-lg border overflow-hidden">
          <div
            ref={floorPlanContainerRef}
            style={{ height: '500px' }}
          >
            <EvacuationRouteDrawer
              floorPlanId={selectedFloor.id}
              floorPlanUrl={selectedFloor.plan_file_url}
              containerWidth={containerDimensions.width || 800}
              containerHeight={containerDimensions.height || 500}
              routes={emergencyPlan.routes.filter(r => r.floor_plan_id === selectedFloor.id)}
              selectedRouteId={selectedRouteId}
              onRouteSelect={onRouteSelect}
              onRouteCreate={onRouteCreate}
              onRouteUpdate={onRouteUpdate}
              onRouteDelete={onRouteDelete}
              isEditing={true}
            />
          </div>
        </div>
      )}

      {editMode === 'routes' && (!selectedFloor || !selectedFloor.plan_file_url) && (
        <div className="bg-gray-50 rounded-lg p-8 text-center text-gray-500">
          Select a floor plan above to edit evacuation routes.
        </div>
      )}

      {/* Checkpoints edit mode */}
      {editMode === 'checkpoints' && selectedFloor && selectedFloor.plan_file_url && (
        <div className="bg-white rounded-lg border overflow-hidden">
          <div
            ref={floorPlanContainerRef}
            style={{ height: '500px' }}
          >
            <CheckpointManager
              floorPlanId={selectedFloor.id}
              floorPlanUrl={selectedFloor.plan_file_url}
              containerWidth={containerDimensions.width || 800}
              containerHeight={containerDimensions.height || 500}
              checkpoints={emergencyPlan.checkpoints.filter(c => c.floor_plan_id === selectedFloor.id)}
              selectedCheckpointId={selectedCheckpointId}
              onCheckpointSelect={onCheckpointSelect}
              onCheckpointCreate={onCheckpointCreate}
              onCheckpointUpdate={onCheckpointUpdate}
              onCheckpointDelete={onCheckpointDelete}
              isEditing={true}
            />
          </div>
        </div>
      )}

      {editMode === 'checkpoints' && (!selectedFloor || !selectedFloor.plan_file_url) && (
        <div className="bg-gray-50 rounded-lg p-8 text-center text-gray-500">
          Select a floor plan above to edit emergency checkpoints.
        </div>
      )}
    </div>
  );
}
