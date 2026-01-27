/**
 * BuildingDetailPage
 *
 * Full-page building detail view at /buildings/:id featuring:
 * - Two-column layout (sidebar + main content)
 * - Building info panel in sidebar
 * - Device monitoring panel in sidebar
 * - Floor selector strip
 * - Unified floor plan viewer with markers + devices + placement mode
 * - Sub-tabs for Alerts and Floor Plan Upload
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useBuildingDetailStore } from '../stores/buildingDetailStore';
import { FloorSelector } from '../components/buildings/FloorSelector';
import { BuildingInfoPanel } from '../components/buildings/BuildingInfoPanel';
import { UnifiedFloorPlanViewer } from '../components/buildings/UnifiedFloorPlanViewer';
import { FloorPlanUpload } from '../components/buildings';
import { DeviceMonitoringPanel } from '../components/devices/DeviceMonitoringPanel';
import { AlertsFloorTable } from '../components/alerts/AlertsFloorTable';
import { Badge, Button, Spinner } from '../components/ui';
import { cn } from '../utils';
import type { HazardLevel } from '../types';

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

type SubTab = 'alerts' | 'upload';

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
    placeDevice,
    addFloorPlan,
    reset,
    clearError,
  } = useBuildingDetailStore();

  const [subTab, setSubTab] = useState<SubTab>('alerts');

  // Load building data on mount
  useEffect(() => {
    if (!id) return;
    fetchBuilding(id);
    fetchFloorPlans(id);
    fetchBuildingAlerts(id);

    return () => {
      reset();
    };
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Handle placement click on floor plan
  const handlePlaceDevice = useCallback(
    (posX: number, posY: number) => {
      if (!placementDeviceId || !selectedFloor) return;
      placeDevice(placementDeviceId, posX, posY, selectedFloor.id);
    },
    [placementDeviceId, selectedFloor, placeDevice]
  );

  // Get unplaced devices for the current floor's building
  const unplacedDevices = devices.filter(
    (d) => d.position_x == null || d.position_y == null
  );

  // Get alerting device IDs
  const alertingDeviceIds = devices
    .filter((d) => d.status === 'alert')
    .map((d) => d.id);

  // Handle floor plan upload complete
  const handleUploadComplete = useCallback(
    (newFloorPlan: typeof floorPlans[0]) => {
      addFloorPlan(newFloorPlan);
      setSubTab('alerts');
    },
    [addFloorPlan]
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

          {/* Floor Plan Viewer */}
          {selectedFloor ? (
            <div className="border rounded-lg overflow-hidden" style={{ height: '500px' }}>
              <UnifiedFloorPlanViewer
                floorPlan={selectedFloor}
                keyLocations={selectedFloor.key_locations || []}
                emergencyExits={selectedFloor.emergency_exits || []}
                fireEquipment={selectedFloor.fire_equipment || []}
                hazards={selectedFloor.hazards || []}
                devices={devices}
                selectedDeviceId={selectedDevice?.id}
                alertingDeviceIds={alertingDeviceIds}
                onDeviceClick={setSelectedDevice}
                isPlacementMode={isPlacementMode}
                onPlaceDevice={handlePlaceDevice}
                showControls
                showLegend
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
